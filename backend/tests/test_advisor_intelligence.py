from backend.services.advisor_intelligence import AdvisorIntelligence


def test_goal_intent():
    assert (
        AdvisorIntelligence.detect_intent(
            "Can I save enough for my car?"
        )
        == "goal"
    )


def test_budget_intent():
    assert (
        AdvisorIntelligence.detect_intent(
            "How can I reduce my spending?"
        )
        == "budget"
    )


def test_subscription_intent():
    assert (
        AdvisorIntelligence.detect_intent(
            "Which subscriptions should I cancel?"
        )
        == "subscription"
    )


def test_forecast_intent():
    assert (
        AdvisorIntelligence.detect_intent(
            "How much will I spend next month?"
        )
        == "forecast"
    )
