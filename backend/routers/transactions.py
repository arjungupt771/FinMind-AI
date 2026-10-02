import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, File, UploadFile  
from pydantic import BaseModel
from backend.services.transaction_csv import parse_csv_transactions
from backend.services.transaction_pipeline import normalize_transaction
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.database.repositories import TransactionRepository
from backend.dependencies import get_current_user_id
from backend.services.transaction_pipeline import normalize_transaction


logger = logging.getLogger(__name__)
router = APIRouter()


class TransactionItem(BaseModel):
    id: str
    date: str
    merchant: str
    amount: float
    type: str
    category: str
    source: str
    description: Optional[str] = None

    @classmethod
    def from_orm_model(cls, tx) -> "TransactionItem":
        return cls(
            id=tx.id,
            date=tx.date.isoformat(),
            merchant=tx.merchant,
            amount=tx.amount,
            type=tx.transaction_type,
            category=tx.category,
            source=tx.source,
            description=tx.description,
        )


class TransactionCreate(BaseModel):
    date: str
    merchant: str
    amount: float
    type: str
    category: str
    source: str
    description: Optional[str] = None


class BulkTransactionResult(BaseModel):
    total: int
    inserted: int
    duplicates: int
    failed: int
    count: int
    transactions: List[TransactionItem] = []
    duplicate_ids: List[str] = []
    errors: List[dict] = []


def _to_model_kwargs(user_id: str, tx: TransactionCreate) -> dict:
    """
    Convert an API transaction into the canonical transaction representation
    before persisting it to the database.
    """

    canonical = normalize_transaction(
        {
            "date": tx.date,
            "merchant": tx.merchant,
            "amount": tx.amount,
            "type": tx.type,
            "category": tx.category,
            "source": tx.source,
            "description": tx.description,
        }
    )

    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        **canonical.to_storage_dict(),
    }


@router.get("/", response_model=List[TransactionItem])
def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List transactions with optional filtering."""

    try:
        repo = TransactionRepository(db)

        results = repo.get_user_transactions(
            user_id=user_id,
            skip=skip,
            limit=limit,
            start_date=(
                datetime.fromisoformat(start_date)
                if start_date
                else None
            ),
            end_date=(
                datetime.fromisoformat(end_date)
                if end_date
                else None
            ),
            category=category,
        )

        return [
            TransactionItem.from_orm_model(tx)
            for tx in results
        ]

    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date filter: {ve}",
        )

    except Exception as e:
        logger.error(
            f"Error listing transactions: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to list transactions",
        )


@router.post("/", response_model=TransactionItem)
def add_transaction(
    transaction: TransactionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Add a new transaction with normalization and duplicate detection."""

    try:
        repo = TransactionRepository(db)

        # Normalize and validate through the canonical pipeline.
        model_kwargs = _to_model_kwargs(
            user_id,
            transaction,
        )

        # Check whether this transaction already exists.
        duplicate = repo.find_duplicate(
            user_id=user_id,
            date=model_kwargs["date"],
            merchant=model_kwargs["merchant"],
            amount=model_kwargs["amount"],
            transaction_type=model_kwargs["transaction_type"],
            category=model_kwargs.get("category"),
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Duplicate transaction detected",
                    "transaction_id": duplicate.id,
                },
            )

        tx = repo.create(model_kwargs)

        logger.info(
            f"Transaction added: {tx.id}"
        )

        return TransactionItem.from_orm_model(tx)

    except HTTPException:
        raise

    except ValueError as e:
        logger.error(
            f"Invalid transaction: {str(e)}"
        )

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        logger.error(
            f"Error adding transaction: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to add transaction",
        )


@router.get(
    "/{transaction_id}",
    response_model=TransactionItem,
)
def get_transaction(
    transaction_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get a specific transaction."""

    repo = TransactionRepository(db)

    tx = repo.get_by_id(transaction_id)

    if not tx or tx.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return TransactionItem.from_orm_model(tx)


@router.put(
    "/{transaction_id}",
    response_model=TransactionItem,
)
def update_transaction(
    transaction_id: str,
    transaction: TransactionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update a transaction using the canonical transaction pipeline."""

    try:
        repo = TransactionRepository(db)

        existing = repo.get_by_id(transaction_id)

        if not existing or existing.user_id != user_id:
            raise HTTPException(
                status_code=404,
                detail="Transaction not found",
            )

        # Normalize through the same canonical pipeline used during creation.
        model_kwargs = _to_model_kwargs(
            user_id,
            transaction,
        )

        # Do not replace the transaction ID or user ID.
        update_data = {
            "date": model_kwargs["date"],
            "merchant": model_kwargs["merchant"],
            "amount": model_kwargs["amount"],
            "transaction_type": model_kwargs["transaction_type"],
            "category": model_kwargs["category"],
            "source": model_kwargs["source"],
            "description": model_kwargs["description"],
        }

        updated = repo.update(
            transaction_id,
            update_data,
        )

        logger.info(
            f"Transaction updated: {transaction_id}"
        )

        return TransactionItem.from_orm_model(updated)

    except HTTPException:
        raise

    except ValueError as e:
        logger.error(
            f"Invalid transaction update: {str(e)}"
        )

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        logger.error(
            f"Error updating transaction: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to update transaction",
        )


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Delete a transaction."""

    repo = TransactionRepository(db)

    existing = repo.get_by_id(transaction_id)

    if not existing or existing.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    repo.delete(transaction_id)

    logger.info(
        f"Transaction deleted: {transaction_id}"
    )

    return {
        "message": "Transaction deleted successfully",
        "id": transaction_id,
    }


@router.post(
    "/bulk-upload",
    response_model=BulkTransactionResult,
)
def bulk_upload_transactions(
    transactions: List[TransactionCreate],
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Bulk upload transactions with normalization, validation,
    duplicate detection, and per-row error reporting.

    The response preserves the legacy `count` and `transactions`
    fields for API compatibility.
    """

    repo = TransactionRepository(db)

    total = len(transactions)
    inserted = 0
    duplicates = 0
    failed = 0

    duplicate_ids: List[str] = []
    errors: List[dict] = []
    created_transactions: List[TransactionItem] = []

    for index, transaction in enumerate(transactions):
        try:
            model_kwargs = _to_model_kwargs(
                user_id,
                transaction,
            )

            duplicate = repo.find_duplicate(
                user_id=user_id,
                date=model_kwargs["date"],
                merchant=model_kwargs["merchant"],
                amount=model_kwargs["amount"],
                transaction_type=model_kwargs["transaction_type"],
                category=model_kwargs.get("category"),
            )

            if duplicate is not None:
                duplicates += 1
                duplicate_ids.append(duplicate.id)
                continue

            tx = repo.create(model_kwargs)

            inserted += 1

            created_transactions.append(
                TransactionItem.from_orm_model(tx)
            )

        except ValueError as e:
            failed += 1

            errors.append(
                {
                    "index": index,
                    "error": str(e),
                }
            )

        except Exception:
            failed += 1

            errors.append(
                {
                    "index": index,
                    "error": "Failed to insert transaction",
                }
            )

            logger.exception(
                "Failed to import transaction at index %s",
                index,
            )

    logger.info(
        "Bulk transaction import completed: "
        "total=%s inserted=%s duplicates=%s failed=%s",
        total,
        inserted,
        duplicates,
        failed,
    )

    return BulkTransactionResult(
        total=total,
        inserted=inserted,
        duplicates=duplicates,
        failed=failed,

        # Backward compatibility
        count=inserted,
        transactions=created_transactions,

        duplicate_ids=duplicate_ids,
        errors=errors,
    )

@router.post("/import-csv")
async def import_transactions_csv(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Import transactions from a CSV file.

    The CSV is parsed into canonical transaction data and then passed
    through the same normalization + duplicate detection pipeline used
    by normal transaction creation.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="CSV file is required",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported",
        )

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="CSV file is empty",
            )

        rows, parse_errors = parse_csv_transactions(content)

        repo = TransactionRepository(db)

        inserted = []
        duplicates = []
        errors = list(parse_errors)

        for index, row in enumerate(rows, start=2):
            try:
                canonical = normalize_transaction(row)

                model_kwargs = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    **canonical.to_storage_dict(),
                }

                duplicate = repo.find_duplicate(
                    user_id=user_id,
                    date=model_kwargs["date"],
                    merchant=model_kwargs["merchant"],
                    amount=model_kwargs["amount"],
                    transaction_type=model_kwargs["transaction_type"],
                    category=model_kwargs["category"],
                )

                if duplicate:
                    duplicates.append(
                        {
                            "row": index,
                            "transaction_id": duplicate.id,
                            "merchant": duplicate.merchant,
                            "date": duplicate.date.isoformat(),
                            "amount": duplicate.amount,
                            "category": duplicate.category,
                        }
                    )
                    continue

                tx = repo.create(model_kwargs)
                inserted.append(
                    TransactionItem.from_orm_model(tx)
                )

            except ValueError as exc:
                errors.append(
                    {
                        "row": index,
                        "error": str(exc),
                    }
                )

            except Exception as exc:
                logger.exception(
                    "Failed to import CSV row %s",
                    index,
                )

                errors.append(
                    {
                        "row": index,
                        "error": "Failed to import transaction",
                    }
                )

        logger.info(
            "CSV transaction import completed: "
            "inserted=%s duplicates=%s failed=%s",
            len(inserted),
            len(duplicates),
            len(errors),
        )

        return {
            "filename": file.filename,
            "total": len(rows) + len(parse_errors),
            "inserted": len(inserted),
            "duplicates": len(duplicates),
            "failed": len(errors),
            "count": len(inserted),
            "transactions": inserted,
            "duplicate_rows": duplicates,
            "errors": errors,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception(
            "CSV transaction import failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to import CSV transactions",
        )