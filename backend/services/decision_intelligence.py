from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.services.financial_intelligence import FinancialIntelligenceEngine
from backend.services.goal_intelligence import GoalIntelligence
from backend.services.recurring_expense_intelligence import RecurringExpenseIntelligence


class CrossDomainIntelligenceEngine:
    """Deterministic cross-module intelligence built from actual user data."""

    def analyze(
        self,
        transactions: List[Dict[str, Any]],
        goals: Optional[List[Any]] = None,
        recurring: Optional[Dict[str, Any]] = None,
        forecast: Optional[Dict[str, Any]] = None,
        health: Optional[Dict[str, Any]] = None,
        anomalies: Optional[List[Dict[str, Any]]] = None,
        memories: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        intelligence = FinancialIntelligenceEngine(period_days=30).analyze(transactions)

        category_totals = {
            item.category: item.amount
            for item in intelligence.top_categories
        }

        goal_risk = []
        for goal in goals or []:
            if goal.get("status") in {"at_risk", "watch", "overdue"}:
                goal_risk.append({
                    "name": goal.get("name"),
                    "status": goal.get("status"),
                    "monthly_shortfall": goal.get("monthly_shortfall", 0),
                    "remaining_amount": goal.get("remaining_amount", 0),
                })

        recurring_cost = (recurring or {}).get("total_monthly_cost", 0.0)
        recurring_patterns = (recurring or {}).get("patterns", [])

        insights: List[Dict[str, Any]] = []

        if goal_risk and intelligence.net_cash_flow < 0:
            insights.append({
                "type": "goal_pressure",
                "summary": "Your current savings flow is not keeping pace with active goals.",
                "details": [
                    f"{item['name']} is {item['status']} and needs more monthly contribution." \
                    for item in goal_risk
                ],
            })

        if recurring_cost and goal_risk:
            insights.append({
                "type": "recurring_pressure",
                "summary": "Recurring expenses are eating into the same monthly capacity needed for goals.",
                "details": [
                    f"Recurring charges are about ₹{recurring_cost:.2f} per month." \
                    if recurring_cost else "Recurring charges are light relative to your goals."
                ],
            })

        if anomalies:
            top_anomaly = anomalies[0]
            if top_anomaly.get("merchant") or top_anomaly.get("category"):
                insights.append({
                    "type": "anomaly_signal",
                    "summary": "One or more transactions deviate materially from your recent pattern.",
                    "details": [
                        f"Recent anomaly: {top_anomaly.get('merchant') or top_anomaly.get('category')} "
                        f"with a deviation around ₹{abs(float(top_anomaly.get('amount', 0) or 0)):.2f}."
                    ],
                })

        if forecast and isinstance(forecast, dict):
            if forecast.get("forecast_type"):
                insights.append({
                    "type": "forecast_signal",
                    "summary": "The current forecast indicates the next period may be tighter than the recent baseline.",
                    "details": [
                        f"Forecast: {forecast.get('forecast_type')} horizon {forecast.get('horizon')}"
                    ],
                })

        if memories:
            active_goals = [m for m in memories if m.get("memory_type") == "goal" and m.get("active")]
            if active_goals:
                insights.append({
                    "type": "memory_context",
                    "summary": "Recent personal financial memory is aligned with the current goal and spending context.",
                    "details": [m.get("content") for m in active_goals[:2]],
                })

        return {
            "period_summary": {
                "total_income": round(intelligence.total_income, 2),
                "total_expense": round(intelligence.total_expense, 2),
                "net_cash_flow": round(intelligence.net_cash_flow, 2),
                "savings_rate": round(intelligence.savings_rate, 2),
            },
            "top_categories": [
                {"category": item.category, "amount": round(item.amount, 2)}
                for item in intelligence.top_categories[:5]
            ],
            "goal_risk": goal_risk,
            "recurring_monthly_cost": round(recurring_cost, 2),
            "insights": insights,
            "overall_summary": (
                "Your largest financial pressure is the relationship between spending, recurring commitments, and goal shortfall."
                if insights else "Your core financial pattern is stable enough that no major cross-domain issue is apparent."
            ),
        }


class RecommendationEngine:
    """Deterministic recommendations grounded in actual user financial data."""

    def generate(
        self,
        transactions: List[Dict[str, Any]],
        goals: Optional[List[Dict[str, Any]]] = None,
        recurring: Optional[Dict[str, Any]] = None,
        health: Optional[Dict[str, Any]] = None,
        anomalies: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        intelligence = FinancialIntelligenceEngine(period_days=30).analyze(transactions)
        goal_analysis = GoalIntelligence().analyze_all(goals or [], transactions)
        recurring_analysis = recurring or {"patterns": [], "total_monthly_cost": 0.0}
        recommendations: List[Dict[str, Any]] = []

        if goal_analysis.get("active_goal_count", 0):
            for item in goal_analysis.get("goals", []) or []:
                if item.get("status") in {"at_risk", "watch"}:
                    recommendations.append({
                        "type": "adjust_goal_contribution",
                        "priority": "high",
                        "title": f"Increase contribution toward {item.get('name')}",
                        "details": [
                            f"Current monthly savings are ₹{item.get('average_monthly_savings', 0):.2f}; "
                            f"the goal needs ₹{item.get('required_monthly_contribution', 0):.2f} per month."
                        ],
                        "supporting_data": {
                            "goal_name": item.get("name"),
                            "required_monthly_contribution": round(item.get("required_monthly_contribution", 0), 2),
                            "monthly_shortfall": round(item.get("monthly_shortfall", 0), 2),
                        },
                    })

        if recurring_analysis.get("patterns"):
            for pattern in recurring_analysis["patterns"][:2]:
                if pattern.get("cancellation_recommended"):
                    recommendations.append({
                        "type": "review_subscription",
                        "priority": "medium",
                        "title": f"Review {pattern.get('merchant', 'subscription')}",
                        "details": [
                            f"This recurring charge is about ₹{pattern.get('monthly_cost', 0):.2f} per month and has a strong cancellation signal."
                        ],
                        "supporting_data": {
                            "merchant": pattern.get("merchant"),
                            "monthly_cost": round(pattern.get("monthly_cost", 0), 2),
                            "potential_savings": round(pattern.get("potential_savings", 0), 2),
                        },
                    })

        for category in intelligence.top_categories[:3]:
            if category.amount > 0 and intelligence.total_expense > 0:
                recommendations.append({
                    "type": "reduce_spending",
                    "priority": "medium",
                    "title": f"Review {category.category} spending",
                    "details": [
                        f"{category.category} accounts for ₹{category.amount:.2f} in your recent spend profile."
                    ],
                    "supporting_data": {
                        "category": category.category,
                        "amount": round(category.amount, 2),
                        "percentage": round(category.percentage, 2),
                    },
                })

        if anomalies:
            recommendations.append({
                "type": "investigate_anomaly",
                "priority": "high",
                "title": "Investigate unusual spending patterns",
                "details": [
                    "An unusual transaction pattern was detected and should be reviewed before it repeats."
                ],
                "supporting_data": {
                    "anomaly_count": len(anomalies),
                    "top_anomaly": anomalies[0].get("merchant") or anomalies[0].get("category"),
                },
            })

        sorted_recommendations = sorted(
            recommendations,
            key=lambda item: ({"high": 3, "medium": 2, "low": 1}.get(item.get("priority"), 0), item.get("type", "")),
            reverse=True,
        )

        return sorted_recommendations[:5]


class ScenarioEngine:
    """Deterministic financial scenario planning."""

    def evaluate(
        self,
        transactions: List[Dict[str, Any]],
        goals: Optional[List[Any]] = None,
        scenario: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        intelligence = FinancialIntelligenceEngine(period_days=30).analyze(transactions)
        goal_analysis = GoalIntelligence().analyze_all(goals or [], transactions)

        baseline_monthly_savings = intelligence.net_cash_flow
        scenario_values = scenario or {}

        income_change = float(scenario_values.get("income_change", 0.0) or 0.0)
        expense_change = float(scenario_values.get("expense_change", 0.0) or 0.0)
        savings_change = float(scenario_values.get("savings_change", 0.0) or 0.0)
        subscription_removal = float(scenario_values.get("subscription_removal", 0.0) or 0.0)

        projected_monthly_savings = baseline_monthly_savings + income_change - expense_change + savings_change + subscription_removal
        projected_cash_flow = intelligence.total_income + income_change - (intelligence.total_expense + expense_change)

        goal_results = []
        for goal in goal_analysis.get("goals", []) or []:
            current_goal = float(goal.get("required_monthly_contribution", 0.0) or 0.0)
            adjusted_goal = max(current_goal - savings_change, 0.0)
            if goal.get("remaining_amount", 0) > 0 and projected_monthly_savings > 0:
                months_to_finish = goal.get("remaining_amount", 0) / max(projected_monthly_savings, 0.01)
                completion_date = datetime.now() + timedelta(days=round(months_to_finish * 30.4375))
            else:
                completion_date = None

            goal_results.append({
                "goal_name": goal.get("name"),
                "baseline_required_monthly_contribution": round(current_goal, 2),
                "scenario_required_monthly_contribution": round(adjusted_goal, 2),
                "projected_completion_date": completion_date.isoformat() if completion_date else None,
                "remaining_amount": round(goal.get("remaining_amount", 0), 2),
            })

        return {
            "baseline": {
                "monthly_income": round(intelligence.total_income, 2),
                "monthly_expense": round(intelligence.total_expense, 2),
                "monthly_savings": round(baseline_monthly_savings, 2),
                "net_cash_flow": round(intelligence.net_cash_flow, 2),
            },
            "scenario": {
                "income_change": round(income_change, 2),
                "expense_change": round(expense_change, 2),
                "savings_change": round(savings_change, 2),
                "subscription_removal": round(subscription_removal, 2),
                "monthly_savings": round(projected_monthly_savings, 2),
                "net_cash_flow": round(projected_cash_flow, 2),
            },
            "changes": {
                "monthly_savings_change": round(projected_monthly_savings - baseline_monthly_savings, 2),
                "net_cash_flow_change": round(projected_cash_flow - intelligence.net_cash_flow, 2),
            },
            "goal_impact": goal_results,
            "summary": (
                "Scenario improves monthly capacity and moves savings forward if the net effect remains positive."
                if projected_monthly_savings >= baseline_monthly_savings
                else "Scenario reduces monthly capacity and will require a tighter spending plan to keep goals on track."
            ),
        }
