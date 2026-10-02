
import os
import json
import logging
from typing import Any, Dict, List, Optional
from google import genai
from pydantic import BaseModel

from backend.services.analytics_context import TransactionContext, build_transaction_context

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_client = None
if GEMINI_API_KEY:
    try:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:  # pragma: no cover - runtime config only
        logger.warning("Failed to initialize Gemini client: %s", exc)


def _get_client():
    global _client
    if _client is None and GEMINI_API_KEY:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


class AIResponse(BaseModel):
    """Structured AI response format — this IS the response_schema passed to Gemini."""
    summary: str
    insights: List[str]
    recommendations: List[str]
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    action_items: List[str] = []
    confidence: float = 0.8


def build_spending_analysis_prompt(context: TransactionContext, custom_question: str = None) -> str:
    top_categories_str = ", ".join(
        f"{cat['category']} (₹{cat['amount']:.0f})"
        for cat in context.top_categories
    )

    return f"""You are FinMind AI, a personal finance advisor for an Indian user.

Financial Context (Last {context.period_days} days):
- Total Income: ₹{context.total_income:.2f}
- Total Expenses: ₹{context.total_expense:.2f}
- Savings Rate: {context.savings_rate:.1f}%
- Average Monthly Expense: ₹{context.average_monthly_expense:.2f}
- Top Spending Categories: {top_categories_str}
- Investment Ratio: {context.investment_ratio:.1f}%

Recent Transactions:
{json.dumps(context.recent_transactions, indent=2)}

Task: Analyze this user's spending patterns and provide:
1. A clear summary of their financial health
2. Key insights about their spending habits
3. 3-5 actionable recommendations to improve savings and financial health
4. Risk level assessment (LOW/MEDIUM/HIGH)
5. Specific action items for this month

{f'Specific question: {custom_question}' if custom_question else ''}

Base every number you mention on the context above — do not estimate or invent figures."""


def build_savings_prompt(context: TransactionContext) -> str:
    return f"""As a financial advisor, analyze this user's savings potential:

Financial Context:
- Income: ₹{context.total_income:.2f}
- Current Savings Rate: {context.savings_rate:.1f}%
- Top Expense Categories: {json.dumps(context.top_categories)}
- Monthly Expense Average: ₹{context.average_monthly_expense:.2f}

Provide specific, actionable savings recommendations that could realistically:
1. Increase their savings rate by 5-10%
2. Target specific categories for reduction
3. Consider their current spending patterns"""


def build_investment_prompt(context: TransactionContext, monthly_budget: float = None) -> str:
    monthly_investable = (context.total_income - context.total_expense) if context.total_income > 0 else 0
    if monthly_budget:
        monthly_investable = monthly_budget

    return f"""As a financial advisor for an Indian investor:

Financial Profile:
- Monthly Income: ₹{context.total_income / max(1, context.period_days // 30):.2f}
- Current Investment Ratio: {context.investment_ratio:.1f}%
- Monthly Surplus: ₹{monthly_investable:.2f}
- Risk Profile: Based on savings rate of {context.savings_rate:.1f}%

Recommend:
1. Allocation strategy (Stocks/Bonds/Gold/Crypto/Mutual Funds)
2. Monthly investment amount
3. Asset allocation percentages
4. Risk assessment for their profile"""


def build_goal_planning_prompt(context: TransactionContext, goals: List[Dict]) -> str:
    goals_str = json.dumps(goals, indent=2)
    return f"""As a financial advisor, help this user achieve their financial goals:

Current Financial Position:
- Monthly Surplus: ₹{(context.total_income - context.total_expense) / max(1, context.period_days // 30):.2f}
- Current Savings Rate: {context.savings_rate:.1f}%
- Average Monthly Expense: ₹{context.average_monthly_expense:.2f}

User Goals:
{goals_str}

Analyze feasibility and create an actionable plan for each goal."""


def build_budget_optimization_prompt(context: TransactionContext) -> str:
    return f"""As a financial advisor, optimize this budget:

Current Spending Breakdown:
{json.dumps(context.top_categories, indent=2)}

Total Monthly Expense: ₹{context.average_monthly_expense:.2f}
Monthly Income: ₹{context.total_income / max(1, context.period_days // 30):.2f}
Current Savings Rate: {context.savings_rate:.1f}%

Suggest:
1. Optimized budget allocation
2. Categories to reduce
3. Realistic targets
4. Monthly budget cap by category"""


async def call_gemini_api_structured(
    prompt: str,
    response_schema,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """
    Requests Gemini's native structured-output mode via the current SDK.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set")
        raise ValueError("Gemini API key not configured")

    client = _get_client()
    if client is None:
        raise ValueError("Gemini client not initialized")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": 0.95,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            },
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini structured API error: {str(e)}")
        raise


async def call_gemini_api(prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """Unstructured call, kept for any caller that just wants raw text."""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set")
        raise ValueError("Gemini API key not configured")

    client = _get_client()
    if client is None:
        raise ValueError("Gemini client not initialized")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": 0.95,
            },
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        raise


def parse_json_response(response_text: str) -> AIResponse:
    """Legacy fence-stripping parser — used only as a fallback below."""
    try:
        json_str = response_text
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]

        data = json.loads(json_str)
        return AIResponse(**data)
    except Exception as e:
        logger.error(f"Failed to parse AI response: {str(e)}")
        return AIResponse(
            summary="Analysis complete. Please review recommendations.",
            insights=["Unable to fully parse response. Please try again."],
            recommendations=["Review your spending patterns manually"],
            risk_level="MEDIUM",
            confidence=0.5
        )


def parse_structured_response(response_text: str, schema_cls=AIResponse) -> AIResponse:
    """
    Parse a structured-mode Gemini response. Tries strict schema validation
    first (the expected path when response_schema was honored), falls back to
    the legacy fence-stripping heuristic, then to a safe default — so a
    malformed reply degrades gracefully instead of raising into the request.
    """
    try:
        return schema_cls.model_validate_json(response_text)
    except Exception:
        return parse_json_response(response_text)


async def analyze_spending(transactions: List[Dict], question: str = None, days: int = 30) -> AIResponse:
    context = build_transaction_context(transactions, days)
    prompt = build_spending_analysis_prompt(context, question)
    return await generate_structured_response(prompt, AIResponse)


async def get_savings_recommendations(transactions: List[Dict], days: int = 30) -> AIResponse:
    context = build_transaction_context(transactions, days)
    prompt = build_savings_prompt(context)
    return await generate_structured_response(prompt, AIResponse)


async def get_investment_suggestions(transactions: List[Dict], monthly_budget: float = None, days: int = 30) -> AIResponse:
    context = build_transaction_context(transactions, days)
    prompt = build_investment_prompt(context, monthly_budget)
    return await generate_structured_response(prompt, AIResponse)


async def plan_goals(transactions: List[Dict], goals: List[Dict], days: int = 30) -> AIResponse:
    context = build_transaction_context(transactions, days)
    prompt = build_goal_planning_prompt(context, goals)
    return await generate_structured_response(prompt, AIResponse)


async def optimize_budget(transactions: List[Dict], days: int = 30) -> AIResponse:
    context = build_transaction_context(transactions, days)
    prompt = build_budget_optimization_prompt(context)
    return await generate_structured_response(prompt, AIResponse)

async def generate_structured_response(
    prompt: str,
    schema_cls=AIResponse,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AIResponse:
    """
    Try Gemini's structured-output mode first. If the installed SDK/model
    combination can't honor response_schema and raises DURING THE CALL ITSELF
    (not just during parsing), fall back to a plain call + legacy parsing
    instead of surfacing a 500 to the caller.
    """
    try:
        response_text = await call_gemini_api_structured(prompt, schema_cls, temperature, max_tokens)
        return parse_structured_response(response_text, schema_cls)
    except Exception as e:
        logger.warning(f"Structured Gemini call failed ({e}); falling back to unstructured call")
        response_text = await call_gemini_api(prompt, temperature, max_tokens)
        return parse_json_response(response_text)

async def generate_monthly_review(transactions: List[Dict], month: str = None) -> AIResponse:
    context = build_transaction_context(transactions, 30)
    prompt = f"""Generate a comprehensive monthly financial review:

Month: {month or 'Current'}
Income: ₹{context.total_income:.2f}
Expenses: ₹{context.total_expense:.2f}
Savings: ₹{context.total_income - context.total_expense:.2f}
Savings Rate: {context.savings_rate:.1f}%

Top Categories: {json.dumps(context.top_categories)}

Provide:
1. Month performance summary
2. Key achievements
3. Areas of concern
4. Action items for next month
5. Financial health score (0-100)"""
    return await generate_structured_response(prompt, AIResponse)


async def explain_financial_health(transactions: List[Dict], health_score: float) -> AIResponse:
    context = build_transaction_context(transactions, 30)
    prompt = f"""Explain this user's financial health score and provide actionable insights:

Financial Health Score: {health_score}/100
Savings Rate: {context.savings_rate:.1f}%
Monthly Surplus: ₹{(context.total_income - context.total_expense):.2f}
Investment Ratio: {context.investment_ratio:.1f}%

Provide:
1. What this score means
2. Strengths to maintain
3. Weaknesses to address
4. Path to improve score by 10 points"""
    return await generate_structured_response(prompt, AIResponse)


class GeminiService:
    """
    Instance-based wrapper for callers (FinancialAdvisorService) that want an
    injectable client rather than bare module functions — also the one place
    that accepts pre-built conversation history for continuity.
    """

    async def financial_advisor_response(
        self,
        question: str,
        context: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AIResponse:
        history_block = ""
        if conversation_history:
            turns = "\n".join(
                f"Q: {item['question']}\n"
                f"A: {item['answer']}"
                for item in conversation_history
            )
            history_block = (
                "\nRECENT CONVERSATION:\n"
                f"{turns}\n"
            )

        intent = (
            context
            .get("copilot", {})
            .get("intent", "general")
        )

        prompt = f"""You are FinMind AI, a professional personal finance copilot for an Indian user.
The deterministic backend has already calculated the financial numbers supplied below.

Use the supplied context as the source of truth. Do not invent, estimate, or recalculate financial figures. If the context does not contain enough information to answer, say so clearly. Treat retrieved past context as background, not as verified financial data.

Detected intent: {intent}
Use the relevant sections of the context for this intent, including goals, recurring expenses, forecast, financial health, anomalies, and transaction history where available. Give practical, clear guidance appropriate for the user's question. Avoid presenting general information as personalized fact.

Return a concise summary, relevant insights, actionable recommendations, a risk level of LOW, MEDIUM, or HIGH, and specific action items when useful. Keep all numeric claims grounded in the supplied context.
{history_block}
QUESTION: {question}

FINANCIAL CONTEXT:
{json.dumps(context, indent=2, default=str)}"""

        return await generate_structured_response(prompt, AIResponse)


def build_spending_analysis_prompt(
    context: TransactionContext,
    custom_question: str = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    top_categories_str = ", ".join(
        f"{cat['category']} (₹{cat['amount']:.0f})"
        for cat in context.top_categories
    )

    history_block = ""
    if conversation_history:
        turns = "\n".join(f"Q: {h['question']}\nA: {h['answer']}" for h in conversation_history)
        history_block = f"\nRecent conversation (for resolving references like 'that' or 'last month'):\n{turns}\n"

    return f"""You are FinMind AI, a personal finance advisor for an Indian user.

Financial Context (Last {context.period_days} days):
- Total Income: ₹{context.total_income:.2f}
- Total Expenses: ₹{context.total_expense:.2f}
- Savings Rate: {context.savings_rate:.1f}%
- Average Monthly Expense: ₹{context.average_monthly_expense:.2f}
- Top Spending Categories: {top_categories_str}
- Investment Ratio: {context.investment_ratio:.1f}%

Recent Transactions:
{json.dumps(context.recent_transactions, indent=2)}
{history_block}
Task: Analyze this user's spending patterns and provide:
1. A clear summary of their financial health
2. Key insights about their spending habits
3. 3-5 actionable recommendations to improve savings and financial health
4. Risk level assessment (LOW/MEDIUM/HIGH)
5. Specific action items for this month

{f'Specific question: {custom_question}' if custom_question else ''}

Base every number you mention on the context above — do not estimate or invent figures."""

async def analyze_spending(
    transactions: List[Dict],
    question: str = None,
    days: int = 30,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> AIResponse:
    context = build_transaction_context(transactions, days)
    prompt = build_spending_analysis_prompt(context, question, conversation_history)
    return await generate_structured_response(prompt, AIResponse)