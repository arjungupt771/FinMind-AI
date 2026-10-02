from backend.analytics.health_score import FinancialHealthScore


def test_empty_transactions_returns_default():
    engine = FinancialHealthScore()
    result = engine.calculate([])
    assert result["score"] == 50
    assert result["grade"] == "C"


def test_high_savings_rate_scores_well():
    engine = FinancialHealthScore()
    transactions = [
        {"amount": 100000, "type": "income", "category": "salary"},
        {"amount": 20000, "type": "expense", "category": "food"},
        {"amount": 15000, "type": "expense", "category": "investment"},
    ]
    result = engine.calculate(transactions)
    assert result["savings_rate"] > 50
    assert "Strong savings rate" in result["strengths"]
    assert result["score"] > 60


def test_high_expense_ratio_flagged_as_weakness():
    engine = FinancialHealthScore()
    transactions = [
        {"amount": 50000, "type": "income", "category": "salary"},
        {"amount": 48000, "type": "expense", "category": "rent"},
    ]
    result = engine.calculate(transactions)
    assert "Expenses are too high" in result["weaknesses"]