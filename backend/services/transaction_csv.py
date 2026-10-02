"""
CSV transaction ingestion utilities.

Responsibilities:
- Detect common CSV column names
- Support Amount and Debit/Credit bank formats
- Support common bank CSV layouts
- Convert CSV rows into canonical transaction input
- Preserve row-level validation errors
"""

import csv
import io
from typing import Any, Dict, List, Tuple


COLUMN_ALIASES = {
    "date": [
        "date",
        "transaction date",
        "txn date",
        "transaction_date",
        "value date",
    ],

    "merchant": [
        "merchant",
        "payee",
        "vendor",
        "name",
        "description",
        "transaction details",
        "narration",
        "remarks",
    ],

    "amount": [
        "amount",
        "transaction amount",
        "value",
    ],

    "debit": [
        "debit",
        "debit amount",
        "withdrawal",
        "withdrawal amount",
        "dr",
    ],

    "credit": [
        "credit",
        "credit amount",
        "deposit",
        "deposit amount",
        "cr",
    ],

    "type": [
        "type",
        "transaction type",
        "transaction_type",
    ],

    "category": [
        "category",
        "transaction category",
    ],

    "source": [
        "source",
        "account",
        "bank",
    ],

    "description": [
        "details",
        "note",
        "memo",
    ],
}


def _normalize_header(value: str) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def _clean_amount(value: Any) -> float:
    """
    Convert a CSV amount value into a numeric magnitude.

    Supports:
    - 1200
    - 1200.50
    - -1200
    - ₹1,200
    - $1,200.50
    - commas and surrounding whitespace
    """
    if value is None:
        raise ValueError("Amount is empty")

    text = str(value).strip()

    if not text:
        raise ValueError("Amount is empty")

    # Remove common currency symbols and separators.
    text = (
        text
        .replace(",", "")
        .replace("₹", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .strip()
    )

    try:
        return float(text)
    except ValueError:
        raise ValueError(f"Invalid amount: {value}")


def _is_present(value: Any) -> bool:
    return (
        value is not None
        and str(value).strip() != ""
    )


def detect_columns(headers: List[str]) -> Dict[str, str]:
    """
    Map canonical fields to actual CSV column names.
    """

    normalized = {
        _normalize_header(header): header
        for header in headers
    }

    mapping: Dict[str, str] = {}

    for canonical, aliases in COLUMN_ALIASES.items():

        for alias in aliases:

            normalized_alias = _normalize_header(alias)

            if normalized_alias in normalized:
                mapping[canonical] = normalized[
                    normalized_alias
                ]
                break

    return mapping


def _extract_amount_and_type(
    row: Dict[str, Any],
    mapping: Dict[str, str],
) -> Tuple[str, str]:
    """
    Resolve transaction amount and type.

    Supported formats:

    1. Amount + Type

       Amount = 500
       Type   = debit

    2. Signed Amount

       Amount = -500

    3. Debit/Credit

       Debit  = 500
       Credit =

    4. Credit/Debit

       Debit  =
       Credit = 500
    """

    amount_column = mapping.get("amount")
    type_column = mapping.get("type")

    debit_column = mapping.get("debit")
    credit_column = mapping.get("credit")

    # ---------------------------------------------------------
    # Debit / Credit format
    # ---------------------------------------------------------

    if debit_column or credit_column:

        debit_value = (
            row.get(debit_column)
            if debit_column
            else None
        )

        credit_value = (
            row.get(credit_column)
            if credit_column
            else None
        )

        debit_present = _is_present(debit_value)
        credit_present = _is_present(credit_value)

        if debit_present and credit_present:
            raise ValueError(
                "Both debit and credit contain values"
            )

        if debit_present:

            amount = _clean_amount(debit_value)

            if not amount:
                raise ValueError(
                    "Invalid debit amount"
                )

            return (
                str(int(amount))
                if amount.is_integer()
                else str(amount)
            ), "expense"

        if credit_present:

            amount = _clean_amount(credit_value)

            if not amount:
                raise ValueError(
                    "Invalid credit amount"
                )

            return (
                str(int(amount))
                if amount.is_integer()
                else str(amount)
            ), "income"

        raise ValueError(
            "Neither debit nor credit contains an amount"
        )

    # ---------------------------------------------------------
    # Amount format
    # ---------------------------------------------------------

    if amount_column:

        raw_amount = _clean_amount(
            row.get(amount_column)
        )

        if not raw_amount:
            raise ValueError(
                "Amount is missing"
            )

        raw_type = (
            str(row.get(type_column))
            .strip()
            .lower()
            if type_column
            and _is_present(row.get(type_column))
            else ""
        )

        # Explicit transaction type.
        if raw_type in {
            "debit",
            "expense",
            "out",
            "spend",
            "withdrawal",
            "dr",
        }:
            return raw_amount, "expense"

        if raw_type in {
            "credit",
            "income",
            "in",
            "deposit",
            "salary",
            "cr",
        }:
            return raw_amount, "income"

            # ---------------------------------------------------------
    # No type supplied
    #
    # Standard CSV:
    #     Merchant,Amount
    #     -> defaults to expense
    #
    # Bank/signed CSV:
    #     Description,Amount
    #     -> positive = income
    #     -> negative = expense
    # ---------------------------------------------------------

    try:
        numeric_amount = float(raw_amount)

        # If the merchant column actually came from a bank-style
        # "Description" column, preserve signed amount semantics.
        merchant_column = mapping.get("merchant", "")
        merchant_header = _normalize_header(merchant_column)

        if merchant_header == "description":
            if numeric_amount < 0:
                amount = abs(numeric_amount)
                transaction_type = "expense"
            else:
                amount = numeric_amount
                transaction_type = "income"

        else:
            # Original FinMind CSV behavior:
            # Amount-only standard CSV rows default to expense.
            amount = abs(numeric_amount)
            transaction_type = "expense"

        if amount.is_integer():
            amount_string = str(int(amount))
        else:
            amount_string = str(amount)

        return amount_string, transaction_type

    except ValueError:
        raise ValueError(
            f"Invalid transaction amount: {raw_amount}"
        )


def parse_csv_transactions(
    content: Any,
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """
    Parse CSV content.

    Accepts either bytes or str.

    Returns:

        valid_rows:
            Raw dictionaries ready for normalize_transaction()

        errors:
            Row-level parsing errors.
    """

    # ---------------------------------------------------------
    # Support both bytes and str
    # ---------------------------------------------------------

    if isinstance(content, bytes):

        try:
            text = content.decode("utf-8-sig")

        except UnicodeDecodeError:

            text = content.decode("latin-1")

    elif isinstance(content, str):

        text = content

    else:

        raise TypeError(
            "CSV content must be bytes or str"
        )

    reader = csv.DictReader(
        io.StringIO(text)
    )

    if not reader.fieldnames:

        raise ValueError(
            "CSV file does not contain a header row"
        )

    mapping = detect_columns(
        reader.fieldnames
    )

    # ---------------------------------------------------------
    # Required fields
    # ---------------------------------------------------------

    required = [
        "date",
        "merchant",
    ]

    missing = [
        field
        for field in required
        if field not in mapping
    ]

    has_amount_format = (
        "amount" in mapping
    )

    has_debit_credit_format = (
        "debit" in mapping
        or "credit" in mapping
    )

    if (
        not has_amount_format
        and not has_debit_credit_format
    ):
        missing.append(
            "amount or debit/credit"
        )

    if missing:

        raise ValueError(
            "Missing required CSV columns: "
            + ", ".join(missing)
        )

    # ---------------------------------------------------------
    # Parse rows
    # ---------------------------------------------------------

    valid_rows: List[
        Dict[str, Any]
    ] = []

    errors: List[
        Dict[str, Any]
    ] = []

    for row_number, row in enumerate(
        reader,
        start=2,
    ):

        try:

            def get_value(
                field: str,
                default=None,
            ):

                column = mapping.get(field)

                if column is None:
                    return default

                value = row.get(column)

                if value is None:
                    return default

                value = str(value).strip()

                return (
                    value
                    if value
                    else default
                )

            amount, transaction_type = (
                _extract_amount_and_type(
                    row,
                    mapping,
                )
            )

            transaction = {
                "date": get_value(
                    "date"
                ),

                "merchant": get_value(
                    "merchant"
                ),

                "amount": str(int(amount)) if float(amount).is_integer() else str(amount),

                "type": transaction_type,

                "category": get_value(
                    "category",
                    "Other",
                ),

                "source": get_value(
                    "source",
                    "csv",
                ),

                "description": get_value(
                    "description"
                ),
            }

            valid_rows.append(
                transaction
            )

        except Exception as exc:

            errors.append(
                {
                    "row": row_number,
                    "error": str(exc),
                }
            )

    return (
        valid_rows,
        errors,
    )