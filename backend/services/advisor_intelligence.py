"""
Deterministic context builder for Financial Advisor / Copilot 2.0.

No LLM calculations happen here.
This module prepares facts that Gemini can safely explain.
"""

from __future__ import annotations

from typing import Any, Dict, List


class AdvisorIntelligence:

    INTENTS = {
        "goal": (
            "goal_planning",
            "goal",
            "target",
            "saving for",
            "save for",
            "save enough for",
            "deadline",
        ),
        "budget": (
            "budget",
            "spending limit",
            "reduce spending",
            "reduce my spending",
            "cut spending",
        ),
        "subscription": (
            "subscription",
            "recurring",
            "membership",
            "cancel",
        ),
        "forecast": (
            "forecast",
            "future spending",
            "next month",
            "predict",
            "prediction",
        ),
        "health": (
            "financial health",
            "health score",
            "doing financially",
            "financial situation",
        ),
        "anomaly": (
            "anomaly",
            "unusual",
            "suspicious",
            "fraud",
            "strange transaction",
        ),
        "saving": (
            "save money",
            "savings",
            "saving rate",
            "save more",
        ),
        "investment": (
            "invest",
            "investment",
            "mutual fund",
            "stocks",
            "portfolio",
        ),
    }

    @classmethod
    def detect_intent(
        cls,
        question: str,
    ) -> str:

        normalized = (
            question or ""
        ).strip().lower()

        for intent, keywords in cls.INTENTS.items():
            if any(
                keyword in normalized
                for keyword in keywords
            ):
                return intent

        return "general"

    @staticmethod
    def build_goal_context(
        goals: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not goals:
            return {
                "goal_count": 0,
                "goals": [],
            }

        return {
            "goal_count": len(goals),
            "goals": goals,
            "at_risk_goals": [
                goal
                for goal in goals
                if goal.get("status")
                in {"at_risk", "overdue"}
            ],
            "on_track_goals": [
                goal
                for goal in goals
                if goal.get("status")
                == "on_track"
            ],
        }

    @staticmethod
    def build_subscription_context(
        intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            "recurring_count": intelligence.get(
                "recurring_count",
                0,
            ),
            "monthly_cost": intelligence.get(
                "total_monthly_cost",
                0,
            ),
            "annual_cost": intelligence.get(
                "total_annual_cost",
                0,
            ),
            "potential_savings": intelligence.get(
                "potential_savings",
                0,
            ),
            "missed_cycle_count": intelligence.get(
                "missed_cycle_count",
                0,
            ),
            "price_change_count": intelligence.get(
                "price_change_count",
                0,
            ),
            "patterns": intelligence.get(
                "patterns",
                [],
            ),
        }

    @staticmethod
    def build_copilot_metadata(
        intent: str,
        goals: Dict[str, Any],
        subscriptions: Dict[str, Any],
    ) -> Dict[str, Any]:

        context_used = [
            "transactions",
            "financial_health",
            "anomalies",
            "forecast",
            "rag_memory",
            "conversation_history",
        ]

        if goals.get("goal_count", 0) > 0:
            context_used.append("goals")

        if subscriptions.get(
            "recurring_count",
            0,
        ) > 0:
            context_used.append(
                "recurring_expenses"
            )

        return {
            "intent": intent,
            "context_used": context_used,
        }