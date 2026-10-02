from datetime import datetime, timedelta

from backend.services.goal_intelligence import GoalIntelligence


class FakeGoal:
    def __init__(
        self,
        target_amount=120000,
        current_amount=20000,
        deadline=None,
        priority=5,
    ):
        self.id = "goal-1"
        self.name = "Emergency Fund"
        self.category = "Emergency"
        self.priority = priority
        self.target_amount = target_amount
        self.current_amount = current_amount
        self.deadline = deadline or (
            datetime.utcnow() + timedelta(days=365)
        )


def test_goal_calculates_required_monthly_contribution():
    goal = FakeGoal()

    transactions = [
        {
            "date": (
                datetime.utcnow()
                - timedelta(days=30)
            ).isoformat(),
            "amount": 50000,
            "type": "income",
            "category": "Salary",
        },
        {
            "date": (
                datetime.utcnow()
                - timedelta(days=20)
            ).isoformat(),
            "amount": 30000,
            "type": "expense",
            "category": "Bills",
        },
    ]

    result = GoalIntelligence().analyze_goal(
        goal,
        transactions,
    )

    assert result["remaining_amount"] == 100000
    assert result["required_monthly_contribution"] > 0
    assert result["progress_percentage"] > 0


def test_goal_is_completed_when_target_reached():
    goal = FakeGoal(
        target_amount=100000,
        current_amount=100000,
    )

    result = GoalIntelligence().analyze_goal(
        goal,
        [],
    )

    assert result["status"] == "completed"
    assert result["remaining_amount"] == 0
    assert result["progress_percentage"] == 100


def test_goal_is_at_risk_without_savings_capacity():
    goal = FakeGoal(
        target_amount=100000,
        current_amount=0,
        deadline=datetime.utcnow()
        + timedelta(days=180),
    )

    transactions = [
        {
            "date": datetime.utcnow().isoformat(),
            "amount": 10000,
            "type": "income",
            "category": "Salary",
        },
        {
            "date": datetime.utcnow().isoformat(),
            "amount": 15000,
            "type": "expense",
            "category": "Bills",
        },
    ]

    result = GoalIntelligence().analyze_goal(
        goal,
        transactions,
    )

    assert result["status"] == "at_risk"


def test_multiple_goals_are_aggregated():
    goals = [
        FakeGoal(
            target_amount=100000,
            current_amount=50000,
        ),
        FakeGoal(
            target_amount=50000,
            current_amount=50000,
        ),
    ]

    result = GoalIntelligence().analyze_all(
        goals,
        [],
    )

    assert result["goal_count"] == 2
    assert result["completed_goal_count"] == 1
    assert result["active_goal_count"] == 1