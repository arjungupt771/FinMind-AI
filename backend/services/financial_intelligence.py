from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class CategorySummary:
    category: str
    amount: float
    percentage: float
    transaction_count: int


@dataclass
class MerchantSummary:
    merchant: str
    amount: float
    percentage: float
    transaction_count: int


@dataclass
class MonthlySummary:
    month: str
    income: float
    expense: float
    net_cash_flow: float


@dataclass
class FinancialIntelligence:
    period_days: int

    transaction_count: int
    income_transaction_count: int
    expense_transaction_count: int

    total_income: float
    total_expense: float
    net_cash_flow: float

    savings_rate: float
    investment_expense: float
    investment_ratio: float

    average_transaction: float
    average_expense_transaction: float
    average_income_transaction: float

    largest_expense: float
    largest_income: float

    top_categories: List[CategorySummary] = field(
        default_factory=list
    )

    top_merchants: List[MerchantSummary] = field(
        default_factory=list
    )

    monthly_summary: List[MonthlySummary] = field(
        default_factory=list
    )

    expense_category_count: int = 0
    income_category_count: int = 0


class FinancialIntelligenceEngine:

    def __init__(self, period_days: int = 30):
        if period_days <= 0:
            raise ValueError("period_days must be greater than zero")

        self.period_days = period_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        transactions: Iterable[Dict[str, Any]],
    ) -> FinancialIntelligence:

        normalized = self._normalize_transactions(
            transactions
        )

        transaction_count = len(normalized)
        expense_transaction_count = sum(
            1
            for tx in normalized
            if tx["type"] == "expense"
        )
        income_transaction_count = sum(
            1
            for tx in normalized
            if tx["type"] == "income"
        )

        if not normalized:
            return self._empty_result()

        latest_date = max(
            tx["date"]
            for tx in normalized
        )

        cutoff_date = (
            latest_date
            - timedelta(days=self.period_days)
        )

        recent = [
            tx
            for tx in normalized
            if tx["date"] >= cutoff_date
        ]

        if not recent:
            return self._empty_result()

        income_transactions = [
            tx
            for tx in recent
            if tx["type"] == "income"
        ]

        expense_transactions = [
            tx
            for tx in recent
            if tx["type"] == "expense"
        ]

        total_income = sum(
            tx["amount"]
            for tx in income_transactions
        )

        total_expense = sum(
            tx["amount"]
            for tx in expense_transactions
        )
        investment_expense = sum(
            abs(tx["amount"])
            for tx in normalized
            if tx["type"] == "expense"
            and tx["category"].strip().lower() == "investments"
        )

        investment_ratio = (
            investment_expense / total_expense * 100
            if total_expense > 0
            else 0.0
        )

        net_cash_flow = (
            total_income
            - total_expense
        )

        savings_rate = (
            (net_cash_flow / total_income) * 100
            if total_income > 0
            else 0.0
        )

        all_amounts = [
            tx["amount"]
            for tx in recent
        ]

        average_transaction = (
            sum(all_amounts) / len(all_amounts)
            if all_amounts
            else 0.0
        )

        average_expense_transaction = (
            total_expense
            / len(expense_transactions)
            if expense_transactions
            else 0.0
        )

        average_income_transaction = (
            total_income
            / len(income_transactions)
            if income_transactions
            else 0.0
        )

        largest_expense = max(
            (
                tx["amount"]
                for tx in expense_transactions
            ),
            default=0.0,
        )

        largest_income = max(
            (
                tx["amount"]
                for tx in income_transactions
            ),
            default=0.0,
        )

        top_categories = self._build_category_summary(
            expense_transactions,
            total_expense,
        )

        top_merchants = self._build_merchant_summary(
            expense_transactions,
            total_expense,
        )

        monthly_summary = self._build_monthly_summary(
            recent,
        )

        expense_categories = {
            tx["category"]
            for tx in expense_transactions
        }

        income_categories = {
            tx["category"]
            for tx in income_transactions
        }

        return FinancialIntelligence(
            period_days=self.period_days,
            transaction_count=transaction_count,
            income_transaction_count=income_transaction_count,
            expense_transaction_count=expense_transaction_count,
            total_income=round(total_income, 2),
            total_expense=round(total_expense, 2),
            net_cash_flow=round(net_cash_flow, 2),
            savings_rate=round(savings_rate, 2),
            investment_expense=investment_expense,
            investment_ratio=investment_ratio,
            average_transaction=round(
                average_transaction,
                2,
            ),
            average_expense_transaction=round(
                average_expense_transaction,
                2,
            ),
            average_income_transaction=round(
                average_income_transaction,
                2,
            ),
            largest_expense=round(
                largest_expense,
                2,
            ),
            largest_income=round(
                largest_income,
                2,
            ),
            top_categories=top_categories,
            top_merchants=top_merchants,
            monthly_summary=monthly_summary,
            expense_category_count=len(
                expense_categories
            ),
            income_category_count=len(
                income_categories
            ),
        )

    # ------------------------------------------------------------------
    # Transaction normalization
    # ------------------------------------------------------------------

    def _normalize_transactions(
        self,
        transactions: Iterable[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert supported transaction representations into one internal
        representation.

        Internal contract:

            {
                "date": datetime,
                "merchant": str,
                "amount": positive float,
                "type": "income" | "expense",
                "category": str,
            }
        """

        normalized: List[Dict[str, Any]] = []

        for transaction in transactions:
            try:
                date = self._parse_date(
                    transaction.get("date")
                )

                if date is None:
                    continue

                raw_amount = transaction.get(
                    "amount"
                )

                if raw_amount is None:
                    continue

                amount = abs(
                    float(raw_amount)
                )

                if amount <= 0:
                    continue

                transaction_type = self._resolve_type(
                    transaction,
                    raw_amount,
                )

                category = str(
                    transaction.get(
                        "category",
                        "Other",
                    )
                    or "Other"
                ).strip()

                merchant = str(
                    transaction.get(
                        "merchant",
                        "Unknown",
                    )
                    or "Unknown"
                ).strip()

                normalized.append(
                    {
                        "date": date,
                        "merchant": merchant,
                        "amount": amount,
                        "type": transaction_type,
                        "category": category,
                    }
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return normalized

    @staticmethod
    def _resolve_type(
        transaction: Dict[str, Any],
        raw_amount: Any,
    ) -> str:
        """
        Resolve transaction type.

        Priority:
            1. transaction_type
            2. type
            3. signed amount
        """

        raw_type = transaction.get(
            "transaction_type"
        )

        if raw_type is None:
            raw_type = transaction.get("type")

        if raw_type is not None:
            normalized = (
                str(raw_type)
                .strip()
                .lower()
            )

            if normalized in {
                "income",
                "credit",
                "in",
                "salary",
                "deposit",
                "cr",
            }:
                return "income"

            if normalized in {
                "expense",
                "debit",
                "out",
                "spend",
                "spending",
                "withdrawal",
                "dr",
            }:
                return "expense"

        # Fallback for signed transaction dictionaries.
        try:
            return (
                "income"
                if float(raw_amount) > 0
                else "expense"
            )
        except (
            TypeError,
            ValueError,
        ):
            raise ValueError(
                "Unable to determine transaction type"
            )

    @staticmethod
    def _parse_date(
        value: Any,
    ) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value

        if not value:
            return None

        return datetime.fromisoformat(
            str(value)
        )

    # ------------------------------------------------------------------
    # Category analytics
    # ------------------------------------------------------------------

    @staticmethod
    def _build_category_summary(
        transactions: List[Dict[str, Any]],
        total_expense: float,
    ) -> List[CategorySummary]:
        totals: Dict[str, float] = defaultdict(float)
        counts: Dict[str, int] = defaultdict(int)

        for transaction in transactions:
            category = transaction["category"]

            totals[category] += transaction["amount"]
            counts[category] += 1

        result = []

        for category, amount in sorted(
            totals.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (
                amount / total_expense * 100
                if total_expense > 0
                else 0.0
            )

            result.append(
                CategorySummary(
                    category=category,
                    amount=round(amount, 2),
                    percentage=round(
                        percentage,
                        2,
                    ),
                    transaction_count=counts[
                        category
                    ],
                )
            )

        return result[:10]

    # ------------------------------------------------------------------
    # Merchant analytics
    # ------------------------------------------------------------------

    @staticmethod
    def _build_merchant_summary(
        transactions: List[Dict[str, Any]],
        total_expense: float,
    ) -> List[MerchantSummary]:
        totals: Dict[str, float] = defaultdict(float)
        counts: Dict[str, int] = defaultdict(int)

        for transaction in transactions:
            merchant = transaction["merchant"]

            totals[merchant] += transaction["amount"]
            counts[merchant] += 1

        result = []

        for merchant, amount in sorted(
            totals.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (
                amount / total_expense * 100
                if total_expense > 0
                else 0.0
            )

            result.append(
                MerchantSummary(
                    merchant=merchant,
                    amount=round(amount, 2),
                    percentage=round(
                        percentage,
                        2,
                    ),
                    transaction_count=counts[
                        merchant
                    ],
                )
            )

        return result[:10]

    # ------------------------------------------------------------------
    # Monthly analytics
    # ------------------------------------------------------------------

    @staticmethod
    def _build_monthly_summary(
        transactions: List[Dict[str, Any]],
    ) -> List[MonthlySummary]:
        monthly: Dict[
            str,
            Dict[str, float],
        ] = defaultdict(
            lambda: {
                "income": 0.0,
                "expense": 0.0,
            }
        )

        for transaction in transactions:
            month = transaction["date"].strftime(
                "%Y-%m"
            )

            if transaction["type"] == "income":
                monthly[month]["income"] += (
                    transaction["amount"]
                )
            else:
                monthly[month]["expense"] += (
                    transaction["amount"]
                )

        result = []

        for month in sorted(monthly):
            income = monthly[month]["income"]
            expense = monthly[month]["expense"]

            result.append(
                MonthlySummary(
                    month=month,
                    income=round(income, 2),
                    expense=round(expense, 2),
                    net_cash_flow=round(
                        income - expense,
                        2,
                    ),
                )
            )

        return result

    # ------------------------------------------------------------------
    # Empty result
    # ------------------------------------------------------------------

    def _empty_result(
        self,
    ) -> FinancialIntelligence:
        return FinancialIntelligence(
            period_days=self.period_days,
            transaction_count=0,
            income_transaction_count=0,
            expense_transaction_count=0,
            total_income=0.0,
            total_expense=0.0,
            net_cash_flow=0.0,
            savings_rate=0.0,
            investment_expense=0.0,
            investment_ratio=0.0,
            average_transaction=0.0,
            average_expense_transaction=0.0,
            average_income_transaction=0.0,
            largest_expense=0.0,
            largest_income=0.0,
            top_categories=[],
            top_merchants=[],
            monthly_summary=[],
            expense_category_count=0,
            income_category_count=0,
        )


def analyze_transactions(
    transactions: Iterable[Dict[str, Any]],
    period_days: int = 30,
) -> FinancialIntelligence:

    engine = FinancialIntelligenceEngine(
        period_days=period_days
    )

    return engine.analyze(transactions)