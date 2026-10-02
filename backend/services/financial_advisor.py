import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.services.gemini_service import GeminiService
from backend.services.analytics_context import (
    build_financial_context,
    FinancialContext,
)
from backend.services.goal_intelligence import (
    GoalIntelligence,
)
from backend.services.financial_memory import (
    FinancialMemoryService,
)
from backend.services.advisor_intelligence import (
    AdvisorIntelligence,
)
from backend.services.decision_intelligence import (
    CrossDomainIntelligenceEngine,
    RecommendationEngine,
    ScenarioEngine,
)
from backend.services.recurring_expense_intelligence import (
    RecurringExpenseIntelligence,
)
from backend.rag.rag_service import (
    retrieve_context_with_citations,
)
from backend.database.repositories import (
    TransactionRepository,
    ForecastRepository,
    ChatHistoryRepository,
    GoalRepository,
)


class FinancialAdvisorService:
    """
    Financial Advisor / Copilot 2.0.

    Deterministic financial data:
        transactions
        health
        anomalies
        forecasts
        goals
        recurring expenses

    Contextual data:
        RAG memory
        conversation history

    Gemini:
        explanation + reasoning over supplied facts
    """

    def __init__(self, db: Session):
        self.db = db

        self.gemini = GeminiService()
        self.memory_service = FinancialMemoryService(db)

        self.transaction_repo = TransactionRepository(db)
        self.forecast_repo = ForecastRepository(db)
        self.chat_history_repo = ChatHistoryRepository(db)
        self.goal_repo = GoalRepository(db)

        self.goal_intelligence = GoalIntelligence()
        self.recurring_intelligence = (
            RecurringExpenseIntelligence()
        )

    async def build_context(
        self,
        user_id: str,
        question: str,
        conversation_id: str,
    ) -> Tuple[
        FinancialContext,
        List[Dict[str, Any]],
        List[Dict[str, str]],
        str,
        Dict[str, Any],
    ]:

        transactions = (
            self.transaction_repo.get_user_transactions(
                user_id,
                limit=10000,
            )
        )

        transaction_dicts = [
            tx.to_dict()
            for tx in transactions
        ]

        financial_context = build_financial_context(
            transaction_dicts
        )

        forecast = (
            self.forecast_repo.get_most_recent(
                user_id
            )
        )

        if forecast:
            financial_context.forecast = {
                "forecast_type": forecast.forecast_type,
                "horizon": forecast.horizon,
                "predictions": forecast.predictions,
                "model_type": forecast.model_type,
            }

        goals = self.goal_repo.get_user_goals(
            user_id=user_id,
        )

        goal_analysis = self.goal_intelligence.analyze_all(
            goals,
            transaction_dicts,
        )

        recurring_analysis = (
            self.recurring_intelligence.analyze(
                transaction_dicts
            )
        )

        rag_context, citations = (
            await retrieve_context_with_citations(
                user_id=user_id,
                question=question,
            )
        )

        intent = AdvisorIntelligence.detect_intent(
            question
        )

        memory_context = self.memory_service.build_context(
            user_id=user_id,
            query=question,
            limit=8,
            intent=intent,
        )

        memory_details = self.memory_service.retrieve(
            user_id=user_id,
            query=question,
            limit=8,
            intent=intent,
        )

        combined_rag_context = "\n\n".join(
            part
            for part in [
                rag_context,
                memory_context,
            ]
            if part
        )

        history_rows = (
            self.chat_history_repo.get_user_history(
                user_id,
                conversation_id=conversation_id,
                limit=5,
            )
        )

        history = [
            {
                "question": row.message,
                "answer": row.response,
            }
            for row in reversed(history_rows)
        ]

        # Decision engines consume the analyzed goal
        # dictionaries returned by GoalIntelligence.
        cross_domain_insights = CrossDomainIntelligenceEngine().analyze(
            transactions=transaction_dicts,
            goals=goals,
            recurring=recurring_analysis,
            forecast=getattr(
            financial_context,
            "forecast",
            None,
            ),
           health=getattr(
                financial_context,
                "health",
                None,
                ),
            anomalies=getattr(
            financial_context,
            "top_anomalies",
            [],),
            memories=memory_details,
            )

        scenario_plan = ScenarioEngine().evaluate(
    transactions=transaction_dicts,
    goals=goals,
    scenario={
        "income_change": 0.0,
        "expense_change": 0.0,
        "savings_change": 0.0,
        "subscription_removal": 0.0,
    },
)

        recommendations = RecommendationEngine().generate(
    transactions=transaction_dicts,
    goals=goals,
    recurring=recurring_analysis,
    anomalies=financial_context.top_anomalies,
)

        intent = AdvisorIntelligence.detect_intent(
            question
        )

        advisor_metadata = (
            AdvisorIntelligence.build_copilot_metadata(
                intent=intent,
                goals=goal_analysis,
                subscriptions=recurring_analysis,
            )
        )

        extra_context = {
            "goals": goal_analysis,
            "recurring_expenses": recurring_analysis,
            "cross_domain_intelligence": cross_domain_insights,
            "scenario_plan": scenario_plan,
            "recommendations": recommendations,
            "copilot": advisor_metadata,
        }

        return (
            financial_context,
            citations,
            history,
            combined_rag_context,
            extra_context,
        )

    async def answer_question(
        self,
        user_id: str,
        question: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        conversation_id = (
            conversation_id
            or str(uuid.uuid4())
        )

        (
            financial_context,
            memory_citations,
            history,
            combined_rag_context,
            extra_context,
        ) = await self.build_context(
            user_id,
            question,
            conversation_id,
        )

        context_payload = {
            **financial_context.to_prompt_dict(),
            **extra_context,
            "relevant_past_context": combined_rag_context,
            "decision_support": {
                "cross_domain_intelligence": (
                    extra_context[
                        "cross_domain_intelligence"
                    ]
                ),
                "scenario_plan": (
                    extra_context[
                        "scenario_plan"
                    ]
                ),
                "recommendations": (
                    extra_context[
                        "recommendations"
                    ]
                ),
            },
        }

        ai_response = (
            await self.gemini.financial_advisor_response(
                question=question,
                context=context_payload,
                conversation_history=history,
            )
        )

        self.chat_history_repo.create(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message": question,
                "response": ai_response.summary,
                "analysis_type": (
                    extra_context[
                        "copilot"
                    ]["intent"]
                ),
            }
        )

        transaction_sources = [
            {
                "source_type": "transaction",
                "transaction_id": item[
                    "transaction"
                ].get("id"),
                "merchant": item[
                    "transaction"
                ].get("merchant"),
                "amount": item[
                    "transaction"
                ].get("amount"),
                "reason": "; ".join(
                    reason["reason"]
                    for reason in item["reasons"]
                ),
            }
            for item in financial_context.top_anomalies
        ]

        goal_sources = [
            {
                "source_type": "goal",
                "goal_id": goal.get(
                    "goal_id"
                ),
                "name": goal.get(
                    "name"
                ),
                "status": goal.get(
                    "status"
                ),
            }
            for goal in extra_context[
                "goals"
            ].get("goals", [])
        ]

        response = {
            **ai_response.model_dump(),
            "conversation_id": conversation_id,
            "intent": extra_context[
                "copilot"
            ]["intent"],
            "context_used": extra_context[
                "copilot"
            ]["context_used"],
            "sources": (
                memory_citations
                + transaction_sources
                + goal_sources
            ),
        }

        self.memory_service.remember_message(
            user_id=user_id,
            message=question,
        )

        return response