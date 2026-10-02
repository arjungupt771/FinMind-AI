"""
Database models for FinMind AI
Uses SQLAlchemy ORM for database operations
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    auth_provider = Column(String(50), default='supabase')  # supabase, google, github

    # Settings
    currency = Column(String(3), default='INR')
    timezone = Column(String(50), default='Asia/Kolkata')
    notification_enabled = Column(Boolean, default=True)

    # Relationships
    transactions = relationship('Transaction', back_populates='user', cascade='all, delete-orphan')
    goals = relationship('Goal', back_populates='user', cascade='all, delete-orphan')
    chat_history = relationship('ChatHistory', back_populates='user', cascade='all, delete-orphan')
    insights = relationship('Insight', back_populates='user', cascade='all, delete-orphan')
    reports = relationship('FinancialReport', back_populates='user', cascade='all, delete-orphan')
    forecasts = relationship('Forecast', back_populates='user', cascade='all, delete-orphan')
    subscriptions = relationship('Subscription', back_populates='user', cascade='all, delete-orphan')

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    financial_memories = relationship(
    "FinancialMemory",
    back_populates="user",
    cascade="all, delete-orphan",
)


class Transaction(Base):
    __tablename__ = 'transactions'
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'date'),
        Index('idx_user_category', 'user_id', 'category'),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)

    date = Column(DateTime, nullable=False)
    merchant = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)  # always stored as a positive magnitude
    transaction_type = Column(String(50), nullable=False)  # 'income' | 'expense'
    category = Column(String(100), nullable=False, index=True)
    source = Column(String(100), nullable=False)  # bank, csv, import
    description = Column(Text, nullable=True)

    # Metadata
    is_recurring = Column(Boolean, default=False)
    is_anomaly = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)  # generic JSON list of strings, portable across DB backends

    # Relationships
    user = relationship('User', back_populates='transactions')

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """
        Serialize to the dict shape the AI/analytics layer expects.
        `amount` is returned SIGNED (negative = expense, positive = income) because
        gemini_service and the forecasting module both key off amount sign; `type` /
        `transaction_type` are also included because health_score keys off the type field.
        """
        signed_amount = abs(self.amount) if self.transaction_type == 'income' else -abs(self.amount)
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'merchant': self.merchant,
            'amount': signed_amount,
            'type': self.transaction_type,
            'transaction_type': self.transaction_type,
            'category': self.category,
            'source': self.source,
            'description': self.description,
        }


class Goal(Base):
    __tablename__ = 'goals'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0)
    deadline = Column(DateTime, nullable=False)
    priority = Column(Integer, default=1)
    status = Column(String(50), default='active')

    user = relationship('User', back_populates='goals')

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatHistory(Base):
    __tablename__ = 'chat_history'
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)

    conversation_id = Column(String(36), nullable=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    analysis_type = Column(String(50), nullable=True)

    user = relationship('User', back_populates='chat_history')

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class FinancialMemory(Base):
    """
    Persistent user-specific financial memory.

    Stores durable facts/preferences extracted from user interactions
    and financial activity.
    """

    __tablename__ = "financial_memories"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )

    memory_type = Column(
        String(50),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    source = Column(
        String(100),
        nullable=False,
    )

    importance = Column(
        Float,
        default=0.5,
        nullable=False,
    )

    confidence = Column(
        Float,
        default=0.8,
        nullable=False,
    )

    active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    superseded_by = Column(
        String(36),
        nullable=True,
    )

    metadata_json = Column(
        JSON,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="financial_memories",
    )

class Insight(Base):
    __tablename__ = 'insights'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)

    insight_type = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    confidence = Column(Float, default=0.8)
    actionable = Column(Boolean, default=True)

    user = relationship('User', back_populates='insights')

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FinancialReport(Base):
    __tablename__ = 'financial_reports'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)

    report_type = Column(String(50), nullable=False)
    period = Column(String(50), nullable=False)
    content = Column(JSON, nullable=False)
    summary = Column(Text, nullable=False)

    user = relationship('User', back_populates='reports')

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Forecast(Base):
    __tablename__ = 'forecasts'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)

    forecast_type = Column(String(50), nullable=False)
    horizon = Column(String(50), nullable=False)
    predictions = Column(JSON, nullable=False)
    confidence_intervals = Column(JSON, nullable=True)
    model_type = Column(String(50), nullable=True)

    user = relationship('User', back_populates='forecasts')

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)

    name = Column(String(255), nullable=False)
    merchant = Column(String(255), nullable=True)
    amount_per_cycle = Column(Float, nullable=False)
    cycle = Column(String(50), default='monthly')
    category = Column(String(100), nullable=False)
    status = Column(String(50), default='active')

    detected_date = Column(DateTime, nullable=False)
    last_transaction_date = Column(DateTime, nullable=True)
    cancellation_recommended = Column(Boolean, default=False)
    potential_savings = Column(Float, nullable=True)

    user = relationship('User', back_populates='subscriptions')

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)