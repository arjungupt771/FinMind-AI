"""
Recurring Expense & Subscription Intelligence.

Detects recurring expenses directly from transaction history and produces
subscription-like insights without requiring a pre-existing subscription
record.

The service is pure and database-independent.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Sequence


CYCLE_DAYS = {
    "weekly": 7,
    "biweekly": 14,
    "monthly": 30,
    "quarterly": 91,
    "yearly": 365,
}


@dataclass
class RecurringPattern:
    merchant: str
    category: str
    transaction_count: int
    average_amount: float
    min_amount: float
    max_amount: float
    amount_variation: float
    cycle: str
    cycle_days: float
    cycle_deviation: float
    confidence: float
    monthly_cost: float
    annual_cost: float
    last_transaction_date: Optional[datetime]
    next_expected_date: Optional[datetime]
    missed_cycle: bool
    price_change_detected: bool
    price_change_percentage: float
    cancellation_recommended: bool
    potential_savings: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant": self.merchant,
            "category": self.category,
            "transaction_count": self.transaction_count,
            "average_amount": round(self.average_amount, 2),
            "min_amount": round(self.min_amount, 2),
            "max_amount": round(self.max_amount, 2),
            "amount_variation": round(self.amount_variation, 4),
            "cycle": self.cycle,
            "cycle_days": round(self.cycle_days, 2),
            "cycle_deviation": round(self.cycle_deviation, 2),
            "confidence": round(self.confidence, 4),
            "monthly_cost": round(self.monthly_cost, 2),
            "annual_cost": round(self.annual_cost, 2),
            "last_transaction_date": (
                self.last_transaction_date.isoformat()
                if self.last_transaction_date
                else None
            ),
            "next_expected_date": (
                self.next_expected_date.isoformat()
                if self.next_expected_date
                else None
            ),
            "missed_cycle": self.missed_cycle,
            "price_change_detected": self.price_change_detected,
            "price_change_percentage": round(
                self.price_change_percentage, 2
            ),
            "cancellation_recommended": self.cancellation_recommended,
            "potential_savings": round(self.potential_savings, 2),
        }


class RecurringExpenseIntelligence:
    """
    Detect recurring expense patterns.

    Expected transaction shape:

    {
        "date": "...",
        "merchant": "...",
        "amount": -499,
        "type": "expense",
        "category": "Entertainment"
    }

    Positive income transactions are ignored.
    """

    def __init__(
        self,
        min_transactions: int = 3,
        max_cycle_deviation: float = 0.30,
        amount_tolerance: float = 0.20,
    ):
        self.min_transactions = min_transactions
        self.max_cycle_deviation = max_cycle_deviation
        self.amount_tolerance = amount_tolerance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        transactions: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        normalized = self._normalize_transactions(transactions)

        if not normalized:
            return self._empty_result()

        groups = self._group_transactions(normalized)

        patterns: List[RecurringPattern] = []

        for merchant_key, merchant_transactions in groups.items():
            pattern = self._detect_pattern(
                merchant_key,
                merchant_transactions,
            )

            if pattern is not None:
                patterns.append(pattern)

        patterns.sort(
            key=lambda item: (
                item.confidence,
                item.annual_cost,
            ),
            reverse=True,
        )

        total_monthly_cost = sum(
            pattern.monthly_cost
            for pattern in patterns
        )

        total_annual_cost = sum(
            pattern.annual_cost
            for pattern in patterns
        )

        potential_savings = sum(
            pattern.potential_savings
            for pattern in patterns
            if pattern.cancellation_recommended
        )

        missed_cycles = sum(
            1 for pattern in patterns if pattern.missed_cycle
        )

        price_changes = sum(
            1
            for pattern in patterns
            if pattern.price_change_detected
        )

        return {
            "recurring_count": len(patterns),
            "total_monthly_cost": round(total_monthly_cost, 2),
            "total_annual_cost": round(total_annual_cost, 2),
            "potential_savings": round(potential_savings, 2),
            "missed_cycle_count": missed_cycles,
            "price_change_count": price_changes,
            "patterns": [
                pattern.to_dict()
                for pattern in patterns
            ],
        }

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def _normalize_transactions(
        self,
        transactions: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        normalized = []

        for tx in transactions:
            try:
                tx_type = str(
                    tx.get(
                        "transaction_type",
                        tx.get("type", ""),
                    )
                ).strip().lower()

                amount = float(tx.get("amount", 0))

                # Database/analytics convention:
                # expense may arrive negative or positive depending on source.
                if tx_type == "income":
                    continue

                if amount == 0:
                    continue

                date_value = tx.get("date")

                if isinstance(date_value, datetime):
                    tx_date = date_value
                else:
                    tx_date = datetime.fromisoformat(
                        str(date_value).replace("Z", "+00:00")
                    )

                merchant = self._normalize_merchant(
                    tx.get("merchant")
                    or tx.get("description")
                    or "Unknown"
                )

                category = str(
                    tx.get("category") or "Other"
                ).strip()

                normalized.append(
                    {
                        "date": tx_date.replace(
                            tzinfo=None
                        ),
                        "merchant": merchant,
                        "category": category,
                        "amount": abs(amount),
                    }
                )

            except Exception:
                continue

        return sorted(
            normalized,
            key=lambda item: item["date"],
        )

    @staticmethod
    def _normalize_merchant(value: Any) -> str:
        merchant = str(value).strip().lower()

        merchant = re.sub(
            r"\b\d{4,}\b",
            "",
            merchant,
        )

        merchant = re.sub(
            r"[^a-z0-9]+",
            " ",
            merchant,
        )

        merchant = re.sub(
            r"\s+",
            " ",
            merchant,
        ).strip()

        return merchant or "unknown"

    # ------------------------------------------------------------------
    # Grouping
    # ------------------------------------------------------------------

    def _group_transactions(
        self,
        transactions: Sequence[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for tx in transactions:
            key = tx["merchant"]
            groups[key].append(tx)

        return groups

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _detect_pattern(
        self,
        merchant: str,
        transactions: List[Dict[str, Any]],
    ) -> Optional[RecurringPattern]:

        if len(transactions) < self.min_transactions:
            return None

        dates = [
            tx["date"]
            for tx in transactions
        ]

        amounts = [
            tx["amount"]
            for tx in transactions
        ]

        intervals = [
            (dates[index] - dates[index - 1]).days
            for index in range(1, len(dates))
        ]

        intervals = [
            interval
            for interval in intervals
            if interval > 0
        ]

        if len(intervals) < 2:
            return None

        cycle_name, cycle_days, cycle_deviation = (
            self._detect_cycle(intervals)
        )

        if cycle_name is None:
            return None

        amount_variation = self._coefficient_of_variation(
            amounts
        )

        amount_consistency = max(
            0.0,
            1.0 - min(
                amount_variation,
                1.0,
            ),
        )

        cycle_consistency = max(
            0.0,
            1.0 - min(
                cycle_deviation / max(
                    cycle_days,
                    1.0,
                ),
                1.0,
            ),
        )

        frequency_score = min(
            len(transactions) / 6.0,
            1.0,
        )

        confidence = (
            0.45 * cycle_consistency
            + 0.35 * amount_consistency
            + 0.20 * frequency_score
        )

        average_amount = mean(amounts)

        monthly_cost = self._monthly_cost(
            average_amount,
            cycle_name,
        )

        annual_cost = monthly_cost * 12

        last_date = dates[-1]

        next_expected_date = self._calculate_next_expected_date(
            last_date,
            cycle_days,
        )

        missed_cycle = self._is_missed_cycle(
            last_date,
            cycle_days,
        )

        price_change_detected, price_change_percentage = (
            self._detect_price_change(amounts)
        )

        category = self._dominant_category(
            transactions
        )

        cancellation_recommended = (
            confidence >= 0.70
            and annual_cost >= 1000
        )

        potential_savings = (
            annual_cost
            if cancellation_recommended
            else 0.0
        )

        return RecurringPattern(
            merchant=merchant,
            category=category,
            transaction_count=len(transactions),
            average_amount=average_amount,
            min_amount=min(amounts),
            max_amount=max(amounts),
            amount_variation=amount_variation,
            cycle=cycle_name,
            cycle_days=cycle_days,
            cycle_deviation=cycle_deviation,
            confidence=confidence,
            monthly_cost=monthly_cost,
            annual_cost=annual_cost,
            last_transaction_date=last_date,
            next_expected_date=next_expected_date,
            missed_cycle=missed_cycle,
            price_change_detected=price_change_detected,
            price_change_percentage=price_change_percentage,
            cancellation_recommended=cancellation_recommended,
            potential_savings=potential_savings,
        )

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------

    def _detect_cycle(
        self,
        intervals: Sequence[int],
    ):
        best_name = None
        best_days = None
        best_deviation = float("inf")

        average_interval = mean(intervals)

        for name, expected_days in CYCLE_DAYS.items():
            deviation = mean(
                abs(
                    interval - expected_days
                )
                for interval in intervals
            )

            relative_deviation = (
                deviation / expected_days
            )

            if (
                relative_deviation
                <= self.max_cycle_deviation
                and deviation < best_deviation
            ):
                best_name = name
                best_days = expected_days
                best_deviation = deviation

        if best_name is None:
            return None, None, None

        return (
            best_name,
            float(best_days),
            float(best_deviation),
        )

    # ------------------------------------------------------------------
    # Amount analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _coefficient_of_variation(
        values: Sequence[float],
    ) -> float:
        if not values:
            return 0.0

        average = mean(values)

        if average == 0:
            return 0.0

        if len(values) == 1:
            return 0.0

        return pstdev(values) / average

    def _detect_price_change(
        self,
        amounts: Sequence[float],
    ):
        if len(amounts) < 4:
            return False, 0.0

        midpoint = len(amounts) // 2

        before = mean(
            amounts[:midpoint]
        )

        after = mean(
            amounts[midpoint:]
        )

        if before == 0:
            return False, 0.0

        percentage = (
            (after - before)
            / before
            * 100
        )

        detected = abs(percentage) >= 10

        return detected, percentage

    # ------------------------------------------------------------------
    # Date/cost helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _monthly_cost(
        amount: float,
        cycle: str,
    ) -> float:
        if cycle == "weekly":
            return amount * 52 / 12

        if cycle == "biweekly":
            return amount * 26 / 12

        if cycle == "monthly":
            return amount

        if cycle == "quarterly":
            return amount / 3

        if cycle == "yearly":
            return amount / 12

        return amount

    @staticmethod
    def _calculate_next_expected_date(
        last_date: datetime,
        cycle_days: float,
    ) -> datetime:
        from datetime import timedelta

        return last_date + timedelta(
            days=round(cycle_days)
        )

    @staticmethod
    def _is_missed_cycle(
        last_date: datetime,
        cycle_days: float,
    ) -> bool:
        from datetime import timedelta

        today = datetime.utcnow()

        expected = last_date + timedelta(
            days=round(cycle_days)
        )

        tolerance = timedelta(
            days=max(2, round(cycle_days * 0.25))
        )

        return today > expected + tolerance

    @staticmethod
    def _dominant_category(
        transactions: Sequence[Dict[str, Any]],
    ) -> str:
        counts = defaultdict(int)

        for tx in transactions:
            counts[tx["category"]] += 1

        return max(
            counts,
            key=counts.get,
        )

    @staticmethod
    def _empty_result():
        return {
            "recurring_count": 0,
            "total_monthly_cost": 0.0,
            "total_annual_cost": 0.0,
            "potential_savings": 0.0,
            "missed_cycle_count": 0,
            "price_change_count": 0,
            "patterns": [],
        }


def analyze_recurring_expenses(
    transactions: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Convenience wrapper."""
    return RecurringExpenseIntelligence().analyze(
        transactions
    )