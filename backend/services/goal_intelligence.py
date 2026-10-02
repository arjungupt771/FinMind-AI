"""
Goal Intelligence Engine for FinMind AI.

All calculations are deterministic.
Gemini should narrate these results, not invent financial numbers.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.utils.datetime import utcnow


class GoalIntelligence:
    """
    Converts stored financial goals + transaction history into
    actionable deterministic goal metrics.
    """

    def __init__(
        self,
        min_monthly_savings: float = 0.0,
    ):
        self.min_monthly_savings = max(0.0, min_monthly_savings)

    @staticmethod
    def _months_between(start: datetime, end: datetime) -> float:
        days = max(0, (end - start).days)
        return max(days / 30.4375, 0.0)

    @staticmethod
    def _monthly_financial_capacity(
        transactions: List[Dict[str, Any]],
        months: int = 3,
    ) -> Dict[str, float]:

        if not transactions:
            return {
                "average_monthly_income": 0.0,
                "average_monthly_expense": 0.0,
                "average_monthly_savings": 0.0,
                "savings_rate": 0.0,
            }

        cutoff = utcnow() - timedelta(days=months * 30)

        income = 0.0
        expense = 0.0

        for tx in transactions:
            try:
                raw_date = tx.get("date")

                if isinstance(raw_date, datetime):
                    tx_date = raw_date
                else:
                    tx_date = datetime.fromisoformat(
                        str(raw_date).replace("Z", "+00:00")
                    )

                tx_date = tx_date.replace(tzinfo=None)

                if tx_date < cutoff:
                    continue

                amount = float(tx.get("amount", 0))

                tx_type = str(
                    tx.get(
                        "transaction_type",
                        tx.get("type", ""),
                    )
                ).lower()

                if tx_type == "income":
                    income += abs(amount)
                elif tx_type == "expense":
                    expense += abs(amount)
                elif amount > 0:
                    income += amount
                elif amount < 0:
                    expense += abs(amount)

            except (TypeError, ValueError):
                continue

        divisor = max(months, 1)

        monthly_income = income / divisor
        monthly_expense = expense / divisor
        monthly_savings = monthly_income - monthly_expense

        savings_rate = (
            monthly_savings / monthly_income * 100
            if monthly_income > 0
            else 0.0
        )

        return {
            "average_monthly_income": monthly_income,
            "average_monthly_expense": monthly_expense,
            "average_monthly_savings": monthly_savings,
            "savings_rate": savings_rate,
        }

    def analyze_goal(
        self,
        goal: Any,
        transactions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        now = utcnow()

        target = max(float(goal.target_amount or 0), 0.0)
        current = max(float(goal.current_amount or 0), 0.0)

        remaining = max(target - current, 0.0)

        deadline = goal.deadline
        if deadline.tzinfo is not None:
            deadline = deadline.replace(tzinfo=None)

        days_remaining = (deadline - now).days

        months_remaining = self._months_between(
            now,
            deadline,
        )

        progress_percentage = (
            min((current / target) * 100, 100.0)
            if target > 0
            else 100.0
        )

        required_monthly = (
            remaining / months_remaining
            if remaining > 0 and months_remaining > 0
            else 0.0
        )

        required_weekly = (
            required_monthly * 12 / 52
            if required_monthly > 0
            else 0.0
        )

        financial_capacity = self._monthly_financial_capacity(
            transactions,
            months=3,
        )

        monthly_savings = financial_capacity[
            "average_monthly_savings"
        ]

        monthly_income = financial_capacity[
            "average_monthly_income"
        ]

        monthly_expense = financial_capacity[
            "average_monthly_expense"
        ]

        affordability_ratio = (
            required_monthly / monthly_savings
            if monthly_savings > 0
            else float("inf")
        )

        monthly_shortfall = max(
            required_monthly - max(monthly_savings, 0.0),
            0.0,
        )

        projected_completion_date: Optional[datetime] = None

        if remaining <= 0:
            projected_completion_date = now

        elif monthly_savings > 0:
            projected_months = remaining / monthly_savings

            projected_completion_date = (
                now + timedelta(
                    days=round(projected_months * 30.4375)
                )
            )

        if remaining <= 0:
            status = "completed"

        elif days_remaining < 0:
            status = "overdue"

        elif monthly_savings <= 0:
            status = "at_risk"

        elif required_monthly <= monthly_savings:
            status = "on_track"

        elif required_monthly <= monthly_savings * 1.25:
            status = "watch"

        else:
            status = "at_risk"

        projected_days_late: Optional[int] = None

        if (
            projected_completion_date
            and projected_completion_date > deadline
        ):
            projected_days_late = (
                projected_completion_date - deadline
            ).days

        recommended_monthly_contribution = min(
            required_monthly,
            max(monthly_savings, 0.0),
        )

        if status == "on_track":
            recommendation = (
                "Maintain the current savings pace."
            )
        elif status == "watch":
            recommendation = (
                "Increase the monthly contribution or "
                "reduce discretionary spending."
            )
        elif status == "at_risk":
            recommendation = (
                "The current savings capacity is insufficient "
                "for the target deadline. Increase savings, "
                "extend the deadline, or reduce the target."
            )
        elif status == "overdue":
            recommendation = (
                "The goal deadline has passed. Re-plan the "
                "target with a new realistic deadline."
            )
        else:
            recommendation = (
                "The target has already been reached."
            )

        return {
            "goal_id": goal.id,
            "name": goal.name,
            "category": goal.category,
            "priority": goal.priority,
            "status": status,
            "target_amount": round(target, 2),
            "current_amount": round(current, 2),
            "remaining_amount": round(remaining, 2),
            "progress_percentage": round(
                progress_percentage,
                2,
            ),
            "deadline": deadline.isoformat(),
            "days_remaining": days_remaining,
            "months_remaining": round(
                months_remaining,
                2,
            ),
            "required_monthly_contribution": round(
                required_monthly,
                2,
            ),
            "required_weekly_contribution": round(
                required_weekly,
                2,
            ),
            "average_monthly_income": round(
                monthly_income,
                2,
            ),
            "average_monthly_expense": round(
                monthly_expense,
                2,
            ),
            "average_monthly_savings": round(
                monthly_savings,
                2,
            ),
            "current_savings_rate": round(
                financial_capacity["savings_rate"],
                2,
            ),
            "affordability_ratio": (
                None
                if affordability_ratio == float("inf")
                else round(
                    affordability_ratio,
                    3,
                )
            ),
            "monthly_shortfall": round(
                monthly_shortfall,
                2,
            ),
            "projected_completion_date": (
                projected_completion_date.isoformat()
                if projected_completion_date
                else None
            ),
            "projected_days_late": projected_days_late,
            "recommended_monthly_contribution": round(
                recommended_monthly_contribution,
                2,
            ),
            "recommendation": recommendation,
        }

    def analyze_all(
        self,
        goals: List[Any],
        transactions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        analyses = [
            self.analyze_goal(goal, transactions)
            for goal in goals
        ]

        analyses.sort(
            key=lambda item: (
                -int(item["priority"]),
                item["days_remaining"],
            )
        )

        active = [
            item
            for item in analyses
            if item["status"] not in {
                "completed",
            }
        ]

        return {
            "goal_count": len(analyses),
            "active_goal_count": len(active),
            "completed_goal_count": sum(
                1
                for item in analyses
                if item["status"] == "completed"
            ),
            "on_track_count": sum(
                1
                for item in analyses
                if item["status"] == "on_track"
            ),
            "watch_count": sum(
                1
                for item in analyses
                if item["status"] == "watch"
            ),
            "at_risk_count": sum(
                1
                for item in analyses
                if item["status"] == "at_risk"
            ),
            "overdue_count": sum(
                1
                for item in analyses
                if item["status"] == "overdue"
            ),
            "total_remaining": round(
                sum(
                    item["remaining_amount"]
                    for item in analyses
                ),
                2,
            ),
            "total_required_monthly": round(
                sum(
                    item["required_monthly_contribution"]
                    for item in active
                ),
                2,
            ),
            "goals": analyses,
        }