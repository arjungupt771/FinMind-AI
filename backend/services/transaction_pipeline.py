

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


ALLOWED_TRANSACTION_TYPES = {"income", "expense"}

DEFAULT_CATEGORY = "Other"
DEFAULT_SOURCE = "manual"


class CanonicalTransaction(BaseModel):
    """
    Canonical transaction representation used between ingestion and storage.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    date: datetime
    merchant: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    transaction_type: str = Field(
        validation_alias=AliasChoices("transaction_type", "type"))
    category: str = Field(default=DEFAULT_CATEGORY, min_length=1, max_length=100)
    source: str = Field(default=DEFAULT_SOURCE, min_length=1, max_length=100)
    description: Optional[str] = None

    @field_validator("transaction_type", mode="before")
    @classmethod
    def normalize_transaction_type(cls, value: Any) -> str:
        if value is None:
            raise ValueError("transaction_type is required")

        normalized = str(value).strip().lower()

        aliases = {
            "income": "income",
            "credit": "income",
            "in": "income",
            "salary": "income",
            "expense": "expense",
            "debit": "expense",
            "out": "expense",
            "spend": "expense",
            "spending": "expense",
        }

        normalized = aliases.get(normalized, normalized)

        if normalized not in ALLOWED_TRANSACTION_TYPES:
            raise ValueError(
                "transaction_type must be either 'income' or 'expense'"
            )

        return normalized

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: Any) -> str:
        if value is None:
            return DEFAULT_CATEGORY

        normalized = str(value).strip()

        return normalized if normalized else DEFAULT_CATEGORY

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value: Any) -> str:
        if value is None:
            return DEFAULT_SOURCE

        normalized = str(value).strip().lower()

        return normalized if normalized else DEFAULT_SOURCE

    @field_validator("merchant", mode="before")
    @classmethod
    def normalize_merchant(cls, value: Any) -> str:
        if value is None:
            raise ValueError("merchant is required")

        normalized = str(value).strip()

        if not normalized:
            raise ValueError("merchant cannot be empty")

        return normalized

    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, value: Any) -> float:
        if value is None:
            raise ValueError("amount is required")

        if isinstance(value, str):
            value = value.strip()
            value = value.replace(",", "")
            value = value.replace("₹", "")
            value = value.replace("$", "")
            value = value.replace("€", "")
            value = value.replace("£", "")

        try:
            amount = abs(float(value))
        except (TypeError, ValueError):
            raise ValueError("amount must be a valid number")

        if amount <= 0:
            raise ValueError("amount must be greater than zero")

        return amount

    @property
    def signed_amount(self) -> float:
        """
        Return the analytics representation.

        Income  -> positive
        Expense -> negative
        """
        if self.transaction_type == "income":
            return self.amount

        return -self.amount

    def to_storage_dict(self) -> Dict[str, Any]:
        """
        Convert the canonical transaction into the existing DB contract.
        """
        return {
            "date": self.date,
            "merchant": self.merchant,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "category": self.category,
            "source": self.source,
            "description": self.description,
        }

    def to_analytics_dict(self) -> Dict[str, Any]:
        """
        Convert into the signed representation consumed by analytics.
        """
        return {
            "date": self.date.isoformat(),
            "merchant": self.merchant,
            "amount": self.signed_amount,
            "type": self.transaction_type,
            "transaction_type": self.transaction_type,
            "category": self.category,
            "source": self.source,
            "description": self.description,
        }


def normalize_transaction(data: Dict[str, Any]) -> CanonicalTransaction:
    """
    Normalize and validate a raw transaction dictionary.
    """
    return CanonicalTransaction(**data)