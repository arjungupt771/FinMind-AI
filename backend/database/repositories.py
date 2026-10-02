"""
Repository pattern for database operations
Provides clean abstraction over database models
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from backend.utils.datetime import utcnow
from backend.database.models import (
    User, Transaction, Goal, ChatHistory, Insight,
    FinancialReport, Forecast, Subscription, FinancialMemory)

logger = logging.getLogger(__name__)


class Repository:
    """Base repository class"""
    
    def __init__(self, db: Session):
        self.db = db


class UserRepository(Repository):
    """User database operations"""
    
    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def create(self, user_data: Dict) -> User:
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update(self, user_id: str, data: Dict) -> User:
        user = self.get_by_id(user_id)
        if user:
            for key, value in data.items():
                setattr(user, key, value)
            user.updated_at = utcnow()
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def update_last_login(self, user_id: str):
        user = self.get_by_id(user_id)
        if user:
            user.last_login = utcnow()
            self.db.commit()


class TransactionRepository(Repository):
    """Transaction database operations"""


    def find_duplicate(
        self,
        user_id: str,
        date: datetime,
        merchant: str,
        amount: float,
        transaction_type: str,
        category: Optional[str] = None,
    ):
        query = (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.date == date,
                Transaction.merchant == merchant,
                Transaction.amount == abs(amount),
                Transaction.transaction_type == transaction_type,
            )
        )

        if category is not None:
            query = query.filter(
                Transaction.category == category
            )

        return query.first()
    
    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    def get_user_transactions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None
    ) -> List[Transaction]:
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        if category:
            query = query.filter(Transaction.category == category)
        
        return query.order_by(desc(Transaction.date)).offset(skip).limit(limit).all()
    
    def get_user_transactions_range(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Transaction]:
        """Get transactions from the last N days"""
        start_date = utcnow() - timedelta(days=days)
        return self.get_user_transactions(
            user_id=user_id,
            start_date=start_date,
            limit=10000
        )
    
    def create(self, transaction_data: Dict) -> Transaction:
        transaction = Transaction(**transaction_data)
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
    
    def bulk_create(self, transactions: List[Dict]) -> List[Transaction]:
        """Create multiple transactions"""
        created = []
        for tx_data in transactions:
            tx = Transaction(**tx_data)
            self.db.add(tx)
            created.append(tx)
        self.db.commit()
        return created
    
    def update(self, transaction_id: str, data: Dict) -> Optional[Transaction]:
        tx = self.get_by_id(transaction_id)
        if tx:
            for key, value in data.items():
                setattr(tx, key, value)
            tx.updated_at = utcnow()
            self.db.commit()
            self.db.refresh(tx)
        return tx
    
    def delete(self, transaction_id: str) -> bool:
        tx = self.get_by_id(transaction_id)
        if tx:
            self.db.delete(tx)
            self.db.commit()
            return True
        return False
    
    def count_by_user(self, user_id: str) -> int:
        return self.db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id
        ).scalar()
    
    def get_categories(self, user_id: str) -> List[str]:
        """Get unique categories for user"""
        return self.db.query(Transaction.category).filter(
            Transaction.user_id == user_id
        ).distinct().all()


class GoalRepository(Repository):
    """Goal database operations"""
    
    def get_by_id(self, goal_id: str) -> Optional[Goal]:
        return self.db.query(Goal).filter(Goal.id == goal_id).first()
    
    def get_user_goals(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Goal]:
        query = self.db.query(Goal).filter(Goal.user_id == user_id)
        if status:
            query = query.filter(Goal.status == status)
        return query.order_by(desc(Goal.priority)).all()
    
    def create(self, goal_data: Dict) -> Goal:
        goal = Goal(**goal_data)
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal
    
    def update(self, goal_id: str, data: Dict) -> Optional[Goal]:
        goal = self.get_by_id(goal_id)
        if goal:
            for key, value in data.items():
                setattr(goal, key, value)
            goal.updated_at = utcnow()
            self.db.commit()
            self.db.refresh(goal)
        return goal
    
    def delete(self, goal_id: str) -> bool:
        goal = self.get_by_id(goal_id)
        if goal:
            self.db.delete(goal)
            self.db.commit()
            return True
        return False


class ChatHistoryRepository(Repository):
    """Chat history database operations"""
    
    def create(self, chat_data: Dict) -> ChatHistory:
        chat = ChatHistory(**chat_data)
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        return chat
    
    def get_user_history(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ChatHistory]:
        query = self.db.query(ChatHistory).filter(ChatHistory.user_id == user_id)
        if conversation_id:
            query = query.filter(ChatHistory.conversation_id == conversation_id)
        return query.order_by(desc(ChatHistory.created_at)).limit(limit).all()


class InsightRepository(Repository):
    """Insight database operations"""
    
    def create(self, insight_data: Dict) -> Insight:
        insight = Insight(**insight_data)
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        return insight
    
    def get_user_insights(
        self,
        user_id: str,
        insight_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Insight]:
        query = self.db.query(Insight).filter(Insight.user_id == user_id)
        if insight_type:
            query = query.filter(Insight.insight_type == insight_type)
        return query.order_by(desc(Insight.created_at)).limit(limit).all()


class ReportRepository(Repository):
    """Financial report database operations"""
    
    def create(self, report_data: Dict) -> FinancialReport:
        report = FinancialReport(**report_data)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report
    
    def get_by_user_period(
        self,
        user_id: str,
        period: str,
        report_type: str
    ) -> Optional[FinancialReport]:
        return self.db.query(FinancialReport).filter(
            FinancialReport.user_id == user_id,
            FinancialReport.period == period,
            FinancialReport.report_type == report_type
        ).first()
    
    def get_user_reports(
        self,
        user_id: str,
        limit: int = 12
    ) -> List[FinancialReport]:
        return self.db.query(FinancialReport).filter(
            FinancialReport.user_id == user_id
        ).order_by(desc(FinancialReport.created_at)).limit(limit).all()


class ForecastRepository(Repository):
    """Forecast database operations"""
    
    def create(self, forecast_data: Dict) -> Forecast:
        forecast = Forecast(**forecast_data)
        self.db.add(forecast)
        self.db.commit()
        self.db.refresh(forecast)
        return forecast
    
    def get_latest(
        self,
        user_id: str,
        forecast_type: str,
        horizon: str
    ) -> Optional[Forecast]:
        return self.db.query(Forecast).filter(
            Forecast.user_id == user_id,
            Forecast.forecast_type == forecast_type,
            Forecast.horizon == horizon
        ).order_by(desc(Forecast.created_at)).first()

    def get_most_recent(self, user_id: str) -> Optional[Forecast]:
        """Get the most recent forecast of a specific type for a user"""
        return self.db.query(Forecast).filter(
            Forecast.user_id == user_id
        ).order_by(desc(Forecast.created_at)).first()


class SubscriptionRepository(Repository):
    """Subscription database operations"""
    
    def create(self, subscription_data: Dict) -> Subscription:
        subscription = Subscription(**subscription_data)
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription
    
    def get_user_subscriptions(
        self,
        user_id: str,
        status: str = 'active'
    ) -> List[Subscription]:
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == status
        ).all()
    
    def get_total_monthly_cost(self, user_id: str) -> float:
        """Calculate total monthly subscription cost"""
        subscriptions = self.get_user_subscriptions(user_id)
        total = 0
        for sub in subscriptions:
            if sub.cycle == 'monthly':
                total += sub.amount_per_cycle
            elif sub.cycle == 'yearly':
                total += sub.amount_per_cycle / 12
            elif sub.cycle == 'weekly':
                total += sub.amount_per_cycle * 4.33  # Approx weeks per month
        return total
    
    def update(self, subscription_id: str, data: Dict) -> Optional[Subscription]:
        sub = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if sub:
            for key, value in data.items():
                setattr(sub, key, value)
            sub.updated_at = utcnow()
            self.db.commit()
            self.db.refresh(sub)
        return sub



class FinancialMemoryRepository(Repository):
    """Persistent financial-memory database operations."""

    def create(self, memory_data: Dict) -> FinancialMemory:
        memory = FinancialMemory(**memory_data)

        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)

        return memory

    def get_by_id(
        self,
        memory_id: str,
    ) -> Optional[FinancialMemory]:
        return (
            self.db.query(FinancialMemory)
            .filter(
                FinancialMemory.id == memory_id
            )
            .first()
        )

    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
    ) -> List[FinancialMemory]:

        query = (
            self.db.query(FinancialMemory)
            .filter(
                FinancialMemory.user_id == user_id
            )
        )

        if active_only:
            query = query.filter(
                FinancialMemory.active.is_(True)
            )

        if memory_type:
            query = query.filter(
                FinancialMemory.memory_type == memory_type
            )

        return (
            query
            .order_by(
                desc(FinancialMemory.importance),
                desc(FinancialMemory.updated_at),
            )
            .limit(limit)
            .all()
        )

    def find_duplicate(
        self,
        user_id: str,
        content: str,
        memory_type: str,
    ) -> Optional[FinancialMemory]:

        return (
            self.db.query(FinancialMemory)
            .filter(
                FinancialMemory.user_id == user_id,
                FinancialMemory.memory_type == memory_type,
                FinancialMemory.content == content,
                FinancialMemory.active.is_(True),
            )
            .first()
        )

    def deactivate(
        self,
        memory_id: str,
    ) -> bool:

        memory = self.get_by_id(memory_id)

        if not memory:
            return False

        memory.active = False
        memory.updated_at = utcnow()

        self.db.commit()

        return True

    def update(
        self,
        memory_id: str,
        data: Dict[str, Any],
    ) -> Optional[FinancialMemory]:

        memory = self.get_by_id(memory_id)

        if not memory:
            return None

        for key, value in data.items():
            setattr(memory, key, value)

        memory.updated_at = utcnow()

        self.db.commit()
        self.db.refresh(memory)

        return memory