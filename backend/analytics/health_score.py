"""
Financial Health 2.0

Calculates a user's financial-health score using the unified
FinancialIntelligenceEngine while preserving the existing response contract.

Phase 4 adds:
- savings-rate intelligence
- investment allocation
- expense burden
- cash-flow consistency
- expense volatility
- category concentration
- transaction activity
- emergency-fund proxy
- richer strengths / weaknesses
"""

from typing import Dict, List, Any
from statistics import pstdev

from backend.services.financial_intelligence import FinancialIntelligenceEngine


class FinancialHealthScore:
    """
    Unified financial health scoring engine.

    The existing calculate() method remains the public entry point.
    """

    def __init__(self):
        self.intelligence_engine = FinancialIntelligenceEngine(period_days=30)

    def calculate(self, transactions: List[Dict]) -> Dict[str, Any]:
        if not transactions:
            return {
                "score": 50,
                "grade": "C",
                "income": 0,
                "expenses": 0,
                "savings": 0,
                "savings_rate": 0,
                "investment_ratio": 0,
                "expense_ratio": 0,
                "cash_flow_consistency": 0,
                "expense_volatility": 0,
                "category_concentration": 0,
                "transaction_count": 0,
                "expense_transaction_count": 0,
                "income_transaction_count": 0,
                "emergency_fund_proxy": 0,
                "strengths": [],
                "weaknesses": ["No transaction history available"],
            }

        from datetime import datetime

        normalized_transactions = []

        for tx in transactions:
            normalized_tx = tx.copy()

            if not normalized_tx.get("date"):
                normalized_tx["date"] = datetime.now().isoformat()

            normalized_transactions.append(normalized_tx)

        intelligence = self.intelligence_engine.analyze(
            normalized_transactions)

        income = float(intelligence.total_income)
        expenses = float(intelligence.total_expense)
        savings = max(income - expenses, 0.0)

        savings_rate = float(intelligence.savings_rate)
        investment_ratio = float(intelligence.investment_ratio)

        expense_ratio = (
            (expenses / income) * 100
            if income > 0
            else 100.0
        )

        transaction_count = int(
            getattr(intelligence, "transaction_count", len(transactions))
        )

        expense_transaction_count = int(
            getattr(
                intelligence,
                "expense_transaction_count",
                sum(
                    1
                    for tx in transactions
                    if self._resolve_type(tx) == "expense"
                ),
            )
        )

        income_transaction_count = int(
            getattr(
                intelligence,
                "income_transaction_count",
                sum(
                    1
                    for tx in transactions
                    if self._resolve_type(tx) == "income"
                ),
            )
        )

        category_concentration = self._calculate_category_concentration(
            intelligence
        )

        expense_volatility = self._calculate_expense_volatility(
            transactions
        )

        cash_flow_consistency = self._calculate_cash_flow_consistency(
            transactions
        )

        emergency_fund_proxy = self._calculate_emergency_fund_proxy(
            income=income,
            expenses=expenses,
            savings=savings,
            savings_rate=savings_rate,
        )

        # ---------------------------------------------------------
        # Base score
        # ---------------------------------------------------------

        score = 0.0

        # Savings: max 30
        score += min(max(savings_rate, 0), 30)

        # Investments: max 20
        score += min(max(investment_ratio, 0), 20)

        # Expense burden: max 20
        if income <= 0:
            score += 0
        elif expense_ratio < 60:
            score += 20
        elif expense_ratio < 70:
            score += 17
        elif expense_ratio < 80:
            score += 14
        elif expense_ratio < 90:
            score += 9
        else:
            score += 4

        # Cash-flow consistency: max 10
        score += cash_flow_consistency * 10

        # Emergency-fund proxy: max 10
        score += emergency_fund_proxy * 10

        # Spending concentration / diversification: max 5
        concentration_score = max(
            0.0,
            min(1.0, 1.0 - category_concentration),
        )
        score += concentration_score * 5

        # Stable transaction activity: max 5
        activity_score = self._activity_score(
            transaction_count,
            expense_transaction_count,
        )
        score += activity_score * 5

        score = max(0, min(round(score), 100))

        strengths = []
        weaknesses = []

        # ---------------------------------------------------------
        # Strengths
        # ---------------------------------------------------------

        if savings_rate >= 20:
            strengths.append("Strong savings rate")
        elif savings_rate >= 10:
            strengths.append("Positive savings behavior")

        if investment_ratio >= 10:
            strengths.append("Healthy investment allocation")
        elif investment_ratio >= 5:
            strengths.append("Some investment allocation")

        if expense_ratio < 70:
            strengths.append("Expenses are well controlled")

        if cash_flow_consistency >= 0.75:
            strengths.append("Consistent cash flow")

        if expense_volatility < 0.35:
            strengths.append("Stable spending pattern")

        if category_concentration < 0.35:
            strengths.append("Spending is reasonably diversified")

        if emergency_fund_proxy >= 0.75:
            strengths.append("Strong emergency-fund capacity")

        # ---------------------------------------------------------
        # Weaknesses
        # ---------------------------------------------------------

        if savings_rate < 10:
            weaknesses.append("Low savings rate")

        if investment_ratio < 5:
            weaknesses.append("Increase investments")

        if expense_ratio > 90:
            weaknesses.append("Expenses are too high")
        elif expense_ratio > 80:
            weaknesses.append("Expense burden is elevated")

        if cash_flow_consistency < 0.45:
            weaknesses.append("Cash flow is inconsistent")

        if expense_volatility > 0.75:
            weaknesses.append("Spending is highly volatile")

        if category_concentration > 0.60:
            weaknesses.append("Spending is concentrated in a few categories")

        if emergency_fund_proxy < 0.35:
            weaknesses.append("Emergency-fund capacity appears limited")

        # Avoid an empty strengths/weaknesses section.
        if not strengths:
            strengths.append("Financial activity is being tracked")

        if not weaknesses:
            weaknesses.append("Continue maintaining current financial habits")

        return {
            "score": score,
            "grade": self._grade(score),

            # Existing fields
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "savings": round(savings, 2),
            "savings_rate": round(savings_rate, 2),
            "investment_ratio": round(investment_ratio, 2),
            "expense_ratio": round(expense_ratio, 2),

            # Phase 4 intelligence
            "cash_flow_consistency": round(
                cash_flow_consistency,
                3,
            ),
            "expense_volatility": round(
                expense_volatility,
                3,
            ),
            "category_concentration": round(
                category_concentration,
                3,
            ),
            "transaction_count": transaction_count,
            "expense_transaction_count": expense_transaction_count,
            "income_transaction_count": income_transaction_count,
            "emergency_fund_proxy": round(
                emergency_fund_proxy,
                3,
            ),

            "strengths": strengths,
            "weaknesses": weaknesses,
        }

    # =============================================================
    # Helpers
    # =============================================================

    @staticmethod
    def _resolve_type(tx: Dict) -> str:
        tx_type = tx.get("transaction_type") or tx.get("type")

        if tx_type:
            normalized = str(tx_type).strip().lower()

            if normalized in {
                "income",
                "credit",
                "in",
                "salary",
            }:
                return "income"

            if normalized in {
                "expense",
                "debit",
                "out",
                "spend",
                "spending",
            }:
                return "expense"

        amount = float(tx.get("amount", 0) or 0)

        return "income" if amount > 0 else "expense"

    @staticmethod
    def _calculate_category_concentration(
        intelligence,
    ) -> float:
        """
        Uses the largest category's share of total spending as a
        simple concentration proxy.

        0 = diversified
        1 = spending entirely concentrated in one category
        """

        categories = getattr(
            intelligence,
            "top_categories",
            [],
        )

        if not categories:
            return 0.0

        percentages = []

        for category in categories:
            if isinstance(category, dict):
                percentage = category.get("percentage")

                if percentage is not None:
                    percentages.append(
                        float(percentage) / 100
                    )

        if not percentages:
            return 0.0

        return max(0.0, min(max(percentages), 1.0))

    @staticmethod
    def _calculate_expense_volatility(
        transactions: List[Dict],
    ) -> float:
        """
        Coefficient of variation for expense amounts.

        Lower = more stable spending.
        Higher = more volatile spending.
        """

        expenses = []

        for tx in transactions:
            if FinancialHealthScore._resolve_type(tx) != "expense":
                continue

            try:
                amount = abs(float(tx.get("amount", 0)))
            except (TypeError, ValueError):
                continue

            if amount > 0:
                expenses.append(amount)

        if len(expenses) < 2:
            return 0.0

        mean = sum(expenses) / len(expenses)

        if mean <= 0:
            return 0.0

        volatility = pstdev(expenses) / mean

        return max(
            0.0,
            min(float(volatility), 1.0),
        )

    @staticmethod
    def _calculate_cash_flow_consistency(
        transactions: List[Dict],
    ) -> float:
        """
        Measures consistency of monthly net cash flow.

        More stable positive cash flow produces a higher score.
        """

        monthly = {}

        for tx in transactions:
            raw_date = tx.get("date")

            if not raw_date:
                continue

            try:
                if hasattr(raw_date, "year"):
                    date = raw_date
                else:
                    from datetime import datetime

                    date = datetime.fromisoformat(
                        str(raw_date).replace("Z", "+00:00")
                    )

                month_key = f"{date.year}-{date.month:02d}"

                amount = abs(float(tx.get("amount", 0)))

                if FinancialHealthScore._resolve_type(tx) == "income":
                    monthly[month_key] = (
                        monthly.get(month_key, 0) + amount
                    )
                else:
                    monthly[month_key] = (
                        monthly.get(month_key, 0) - amount
                    )

            except (TypeError, ValueError):
                continue

        values = list(monthly.values())

        if not values:
            return 0.0

        if len(values) == 1:
            return 1.0 if values[0] >= 0 else 0.35

        positive_months = sum(
            1 for value in values if value >= 0
        )

        positive_ratio = positive_months / len(values)

        mean_abs = (
            sum(abs(value) for value in values)
            / len(values)
        )

        if mean_abs == 0:
            stability = 1.0
        else:
            variation = pstdev(values) / mean_abs
            stability = max(
                0.0,
                min(1.0, 1.0 - variation),
            )

        return max(
            0.0,
            min(
                1.0,
                positive_ratio * 0.7 + stability * 0.3,
            ),
        )

    @staticmethod
    def _calculate_emergency_fund_proxy(
        income: float,
        expenses: float,
        savings: float,
        savings_rate: float,
    ) -> float:
        """
        This is NOT an actual emergency-fund balance.

        It estimates emergency-fund capacity from recent savings behavior.
        """

        if income <= 0 or expenses <= 0:
            return 0.0

        if savings_rate <= 0:
            return 0.0

        # Approximate monthly surplus in units of monthly expenses.
        monthly_surplus_ratio = savings / expenses

        return max(
            0.0,
            min(
                1.0,
                (
                    min(savings_rate / 30.0, 1.0) * 0.6
                    + min(monthly_surplus_ratio / 0.5, 1.0) * 0.4
                ),
            ),
        )

    @staticmethod
    def _activity_score(
        transaction_count: int,
        expense_transaction_count: int,
    ) -> float:
        if transaction_count <= 0:
            return 0.0

        if expense_transaction_count <= 0:
            return 0.25

        if transaction_count >= 10:
            return 1.0

        return min(
            transaction_count / 10,
            1.0,
        )

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "A+"
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 60:
            return "C"
        if score >= 50:
            return "D"
        return "F"