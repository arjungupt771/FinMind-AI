from datetime import datetime, timedelta

from backend.analytics.health_score import FinancialHealthScore
from backend.analytics.anomaly_detection import AnomalyDetector


def make_transaction(
    days_ago,
    amount,
    tx_type,
    category,
    merchant,
):
    return {
        "id": f"{days_ago}-{merchant}-{amount}",
        "date": (
            datetime.now() - timedelta(days=days_ago)
        ).isoformat(),
        "amount": amount,
        "type": tx_type,
        "category": category,
        "merchant": merchant,
    }


def test_phase4_health_score_contains_new_metrics():
    transactions = [
        make_transaction(
            10,
            50000,
            "income",
            "salary",
            "Company",
        ),
        make_transaction(
            9,
            -5000,
            "expense",
            "food",
            "Restaurant",
        ),
        make_transaction(
            8,
            -3000,
            "expense",
            "transport",
            "Uber",
        ),
        make_transaction(
            7,
            -5000,
            "expense",
            "investment",
            "Mutual Fund",
        ),
    ]

    result = FinancialHealthScore().calculate(
        transactions
    )

    assert "score" in result
    assert "grade" in result
    assert "savings_rate" in result
    assert "investment_ratio" in result
    assert "cash_flow_consistency" in result
    assert "expense_volatility" in result
    assert "category_concentration" in result
    assert "emergency_fund_proxy" in result


def test_phase4_empty_transactions():
    result = FinancialHealthScore().calculate([])

    assert result["score"] == 50
    assert result["grade"] == "C"
    assert result["income"] == 0
    assert result["expenses"] == 0


def test_phase5_merchant_behavior_anomaly():
    detector = AnomalyDetector()

    transactions = [
        make_transaction(
            30,
            -100,
            "expense",
            "shopping",
            "Amazon",
        ),
        make_transaction(
            20,
            -120,
            "expense",
            "shopping",
            "Amazon",
        ),
        make_transaction(
            10,
            -110,
            "expense",
            "shopping",
            "Amazon",
        ),
        make_transaction(
            1,
            -1000,
            "expense",
            "shopping",
            "Amazon",
        ),
    ]

    result = detector.detect_merchant_behavior_anomalies(
        transactions
    )

    assert result
    assert result[0]["merchant"] == "Amazon"
    assert result[0]["multiple_of_baseline"] >= 3


def test_phase5_spending_velocity():
    detector = AnomalyDetector()

    base = datetime.now()

    transactions = []

    for index in range(5):
        transactions.append(
            {
                "id": str(index),
                "date": (
                    base + timedelta(hours=index * 2)
                ).isoformat(),
                "amount": -100,
                "type": "expense",
                "category": "shopping",
                "merchant": f"Merchant-{index}",
            }
        )

    result = detector.detect_spending_velocity_anomalies(
        transactions,
        window_hours=24,
        minimum_transactions=4,
    )

    assert result
    assert result[0]["transaction_count"] >= 4


def test_phase5_score_transactions_contains_new_signals():
    detector = AnomalyDetector()

    transactions = [
        make_transaction(
            30,
            -100,
            "expense",
            "shopping",
            "Amazon",
        ),
        make_transaction(
            20,
            -120,
            "expense",
            "shopping",
            "Amazon",
        ),
        make_transaction(
            10,
            -110,
            "expense",
            "shopping",
            "Amazon",
        ),
        make_transaction(
            1,
            -1000,
            "expense",
            "shopping",
            "Amazon",
        ),
        make_transaction(
            1,
            -500,
            "food",
            "restaurant",
            "Restaurant",
        ),
        make_transaction(
            1,
            -600,
            "food",
            "restaurant",
            "Restaurant",
        ),
        make_transaction(
            1,
            -700,
            "food",
            "restaurant",
            "Restaurant",
        ),
        make_transaction(
            1,
            -800,
            "food",
            "restaurant",
            "Restaurant",
        ),
        make_transaction(
            1,
            -900,
            "food",
            "restaurant",
            "Restaurant",
        ),
    ]

    result = detector.score_transactions(
        transactions
    )

    assert isinstance(result, list)

    if result:
        assert "transaction" in result[0]
        assert "score" in result[0]
        assert "reasons" in result[0]
        assert "severity" in result[0]