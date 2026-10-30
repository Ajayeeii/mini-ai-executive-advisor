
from decimal import Decimal, InvalidOperation


# --------------------------------------------------
# FINANCIAL INPUT VALIDATION
# --------------------------------------------------

def validate_amount(value, field_name):
    """
    Validates a financial amount.

    Decimal is used to avoid floating-point
    precision problems in financial calculations.
    """

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a valid number."
        )

    try:
        amount = Decimal(str(value))

    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(
            f"{field_name} must be a valid number."
        )

    if not amount.is_finite():
        raise ValueError(
            f"{field_name} must be finite."
        )

    if amount < 0:
        raise ValueError(
            f"{field_name} cannot be negative."
        )

    return amount


# --------------------------------------------------
# FINANCIAL CALCULATIONS
# --------------------------------------------------

def calculate_financial_metrics(
    revenue,
    cost_of_goods_sold,
    operating_expenses
):
    """
    Calculates basic business financial metrics.

    All monetary calculations use Decimal.

    Returns:
        Dictionary containing:
        - revenue
        - cost_of_goods_sold
        - operating_expenses
        - total_expenses
        - gross_profit
        - net_profit
        - gross_profit_margin
        - net_profit_margin

    Margins are returned as percentages.
    They are None when revenue is zero.
    """

    # STEP 1: Validate inputs.

    revenue = validate_amount(
        revenue,
        "Revenue"
    )

    cost_of_goods_sold = validate_amount(
        cost_of_goods_sold,
        "Cost of goods sold"
    )

    operating_expenses = validate_amount(
        operating_expenses,
        "Operating expenses"
    )

    # STEP 2: Calculate total expenses.

    total_expenses = (
        cost_of_goods_sold + operating_expenses
    )

    # STEP 3: Calculate gross profit.

    gross_profit = (
        revenue - cost_of_goods_sold
    )

    # STEP 4: Calculate net profit.

    net_profit = (
        revenue - total_expenses
    )

    # STEP 5: Calculate profit margins.

    if revenue == 0:

        gross_profit_margin = None
        net_profit_margin = None

    else:

        gross_profit_margin = (
            gross_profit / revenue
        ) * Decimal("100")

        net_profit_margin = (
            net_profit / revenue
        ) * Decimal("100")

    # STEP 6: Return calculated results.

    return {
        "revenue": revenue,
        "cost_of_goods_sold": cost_of_goods_sold,
        "operating_expenses": operating_expenses,
        "total_expenses": total_expenses,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "gross_profit_margin": gross_profit_margin,
        "net_profit_margin": net_profit_margin
    }


import re

from knowledge_assistant import search_documents


def extract_financial_inputs(passages):
    """
    Extracts revenue, cost of goods sold, and operating
    expenses from retrieved document passages.

    Raises ValueError if a required figure is missing
    or conflicting values are found.
    """

    labels = {
        "revenue": r"Total Revenue",
        "cost_of_goods_sold": r"Total Cost of Goods Sold",
        "operating_expenses": r"Total Operating Expenses",
    }

    extracted = {}

    for field, label in labels.items():
        pattern = re.compile(
    rf"\b{label}\s*:\s*\$?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE
)

        matches = []

        for passage in passages:
            text = passage.get("text", "")
            matches.extend(pattern.findall(text))

        # Remove thousands separators before comparison.
        normalized = {value.replace(",", "") for value in matches}

        if not normalized:
            raise ValueError(
                f"Could not find {field.replace('_', ' ')} "
                "in the retrieved documents."
            )

        if len(normalized) > 1:
            raise ValueError(
                f"Conflicting values found for "
                f"{field.replace('_', ' ')}."
            )

        extracted[field] = next(iter(normalized))

    return extracted


def analyze_financial_document(user_id, role, db_path=None):
    """
    Retrieves financial information from accessible documents,
    extracts the required figures, and calculates financial metrics.

    Returns calculations together with document source information.
    """

    question = (
        "Find the 2025 total revenue, total cost of goods sold, "
        "and total operating expenses."
    )

    search_options = {
        "user_id": user_id,
        "role": role,
        "question": question,
    }

    if db_path is not None:
        search_options["db_path"] = db_path

    passages = search_documents(**search_options)

    if not passages:
        raise ValueError(
            "No relevant financial documents were found "
            "or accessible to this user."
        )

    # Extract figures from retrieved document evidence.
    inputs = extract_financial_inputs(passages)

    # Calculate metrics using the existing Decimal function.
    metrics = calculate_financial_metrics(
        revenue=inputs["revenue"],
        cost_of_goods_sold=inputs["cost_of_goods_sold"],
        operating_expenses=inputs["operating_expenses"],
    )

    # Preserve source information for traceability.
    sources = []
    seen_sources = set()

    for passage in passages:
        source = {
            "document_id": passage.get("document_id"),
            "file_name": passage.get("file_name"),
            "page_number": passage.get("page_number"),
            "section": passage.get("section"),
        }

        source_key = tuple(source.values())

        if source_key not in seen_sources:
            sources.append(source)
            seen_sources.add(source_key)

    return {
        "financial_inputs": inputs,
        "metrics": metrics,
        "sources": sources,
    }
