
import pytest
from decimal import Decimal

from finance_advisor import calculate_financial_metrics


# --------------------------------------------------
# TEST 1: CORRECT FINANCIAL CALCULATIONS
# --------------------------------------------------

def test_calculate_financial_metrics():

    result = calculate_financial_metrics(
        revenue="100000",
        cost_of_goods_sold="40000",
        operating_expenses="25000"
    )

    assert result["total_expenses"] == Decimal("65000")
    assert result["gross_profit"] == Decimal("60000")
    assert result["net_profit"] == Decimal("35000")

    assert result["gross_profit_margin"] == Decimal("60.0")
    assert result["net_profit_margin"] == Decimal("35.00")


# --------------------------------------------------
# TEST 2: ZERO REVENUE
# --------------------------------------------------

def test_zero_revenue():

    result = calculate_financial_metrics(
        revenue="0",
        cost_of_goods_sold="0",
        operating_expenses="0"
    )

    assert result["net_profit"] == Decimal("0")
    assert result["gross_profit"] == Decimal("0")

    assert result["gross_profit_margin"] is None
    assert result["net_profit_margin"] is None


# --------------------------------------------------
# TEST 3: NEGATIVE VALUES
# --------------------------------------------------

def test_negative_revenue():

    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_financial_metrics(
            revenue="-100",
            cost_of_goods_sold="40",
            operating_expenses="25"
        )


def test_negative_expenses():

    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_financial_metrics(
            revenue="100",
            cost_of_goods_sold="-40",
            operating_expenses="25"
        )


# --------------------------------------------------
# TEST 4: INVALID TEXT INPUT
# --------------------------------------------------

def test_invalid_financial_input():

    with pytest.raises(ValueError, match="must be a valid number"):
        calculate_financial_metrics(
            revenue="invalid",
            cost_of_goods_sold="40",
            operating_expenses="25"
        )


# --------------------------------------------------
# TEST 5: DECIMAL PRECISION
# --------------------------------------------------

def test_decimal_precision():

    result = calculate_financial_metrics(
        revenue="0.30",
        cost_of_goods_sold="0.10",
        operating_expenses="0.10"
    )

    assert result["net_profit"] == Decimal("0.10")
    assert result["gross_profit"] == Decimal("0.20")


# --------------------------------------------------
# TEST 6: SPECIAL NUMERIC VALUES
# --------------------------------------------------

@pytest.mark.parametrize(
    "invalid_value",
    ["NaN", "Infinity", "-Infinity"]
)
def test_invalid_special_numeric_values(invalid_value):

    with pytest.raises(ValueError, match="must be finite"):

        calculate_financial_metrics(
            revenue=invalid_value,
            cost_of_goods_sold="40",
            operating_expenses="25"
        )
