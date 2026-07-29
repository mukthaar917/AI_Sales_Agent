import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.services.quotation_service import (
    calculate_line,
    calculate_totals,
    round_money,
)


CUSTOMERS_URL = "/api/v1/customers"
PRODUCTS_URL = "/api/v1/products"
QUOTATIONS_URL = "/api/v1/quotations"


# ============================================================
# Helper functions
# ============================================================


def build_customer_payload() -> dict:
    """Build a valid customer request body."""
    unique_value = uuid.uuid4().hex[:12]

    return {
        "company_name": f"ABC Technologies {unique_value}",
        "contact_name": "John Smith",
        "email": f"sales-{unique_value}@example.com",
        "phone": "+1-555-123-4567",
        "website": "https://example.com",
        "address": "123 Main Street",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "postal_code": "10001",
        "tax_number": f"TAX-{unique_value}",
        "notes": "Quotation test customer",
    }


def build_product_payload() -> dict:
    """Build a valid product request body."""
    unique_value = uuid.uuid4().hex[:12]

    return {
        "sku": f"AI-QUOTE-{unique_value}",
        "name": "AI Email Automation",
        "description": "AI-powered email automation solution",
        "unit": "License",
        "unit_price": 500.00,
        "currency": "USD",
        "tax_rate": 18.00,
    }


def create_test_customer(
    client: TestClient,
    auth_headers: dict[str, str],
) -> dict:
    """Create and return a customer using the API."""
    response = client.post(
        CUSTOMERS_URL,
        json=build_customer_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_test_product(
    client: TestClient,
    auth_headers: dict[str, str],
) -> dict:
    """Create and return a product using the API."""
    response = client.post(
        PRODUCTS_URL,
        json=build_product_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


def build_quotation_payload(
    customer_id: str,
    product_id: str | None,
) -> dict:
    """Build a valid quotation request body."""
    return {
        "customer_id": customer_id,
        "issue_date": "2026-07-29",
        "expiry_date": "2026-08-28",
        "currency": "USD",
        "notes": "Sample quotation",
        "terms": "Net 30 Days",
        "items": [
            {
                "product_id": product_id,
                "description": "AI Email Automation",
                "quantity": 2,
                "unit": "License",
                "unit_price": 500.00,
                "discount_rate": 10.00,
                "tax_rate": 18.00,
                "sort_order": 1,
            }
        ],
    }


def create_test_quotation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> dict:
    """Create the required customer, product, and quotation."""
    customer = create_test_customer(
        client=client,
        auth_headers=auth_headers,
    )

    product = create_test_product(
        client=client,
        auth_headers=auth_headers,
    )

    payload = build_quotation_payload(
        customer_id=customer["id"],
        product_id=product["id"],
    )

    response = client.post(
        QUOTATIONS_URL,
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


# ============================================================
# Calculation tests
# ============================================================


class TestRoundMoney:
    def test_rounds_to_two_decimal_places(self) -> None:
        result = round_money(Decimal("10.125"))

        assert result == Decimal("10.13")

    def test_rounds_down_correctly(self) -> None:
        result = round_money(Decimal("10.124"))

        assert result == Decimal("10.12")

    def test_preserves_two_decimal_places(self) -> None:
        result = round_money(Decimal("500.00"))

        assert result == Decimal("500.00")


class TestCalculateLine:
    def test_calculates_line_with_discount_and_tax(self) -> None:
        result = calculate_line(
            quantity=Decimal("2"),
            unit_price=Decimal("500"),
            discount_rate=Decimal("10"),
            tax_rate=Decimal("18"),
        )

        assert result["subtotal"] == Decimal("1000.00")
        assert result["discount_amount"] == Decimal("100.00")
        assert result["tax_amount"] == Decimal("162.00")
        assert result["line_total"] == Decimal("1062.00")

    def test_calculates_line_without_discount(self) -> None:
        result = calculate_line(
            quantity=Decimal("3"),
            unit_price=Decimal("100"),
            discount_rate=Decimal("0"),
            tax_rate=Decimal("18"),
        )

        assert result["subtotal"] == Decimal("300.00")
        assert result["discount_amount"] == Decimal("0.00")
        assert result["tax_amount"] == Decimal("54.00")
        assert result["line_total"] == Decimal("354.00")

    def test_calculates_line_without_tax(self) -> None:
        result = calculate_line(
            quantity=Decimal("2"),
            unit_price=Decimal("250"),
            discount_rate=Decimal("10"),
            tax_rate=Decimal("0"),
        )

        assert result["subtotal"] == Decimal("500.00")
        assert result["discount_amount"] == Decimal("50.00")
        assert result["tax_amount"] == Decimal("0.00")
        assert result["line_total"] == Decimal("450.00")

    def test_calculates_line_without_discount_or_tax(self) -> None:
        result = calculate_line(
            quantity=Decimal("4"),
            unit_price=Decimal("125"),
            discount_rate=Decimal("0"),
            tax_rate=Decimal("0"),
        )

        assert result["subtotal"] == Decimal("500.00")
        assert result["discount_amount"] == Decimal("0.00")
        assert result["tax_amount"] == Decimal("0.00")
        assert result["line_total"] == Decimal("500.00")

    def test_calculates_decimal_quantity(self) -> None:
        result = calculate_line(
            quantity=Decimal("1.50"),
            unit_price=Decimal("99.99"),
            discount_rate=Decimal("5"),
            tax_rate=Decimal("18"),
        )

        assert result["subtotal"] == Decimal("149.99")
        assert result["discount_amount"] == Decimal("7.50")
        assert result["tax_amount"] == Decimal("25.65")
        assert result["line_total"] == Decimal("168.14")

    def test_calculates_zero_price(self) -> None:
        result = calculate_line(
            quantity=Decimal("1"),
            unit_price=Decimal("0"),
            discount_rate=Decimal("0"),
            tax_rate=Decimal("18"),
        )

        assert result["subtotal"] == Decimal("0.00")
        assert result["discount_amount"] == Decimal("0.00")
        assert result["tax_amount"] == Decimal("0.00")
        assert result["line_total"] == Decimal("0.00")

    @pytest.mark.parametrize(
        (
            "quantity",
            "unit_price",
            "discount_rate",
            "tax_rate",
            "expected_total",
        ),
        [
            (
                Decimal("1"),
                Decimal("100"),
                Decimal("0"),
                Decimal("0"),
                Decimal("100.00"),
            ),
            (
                Decimal("2"),
                Decimal("100"),
                Decimal("10"),
                Decimal("0"),
                Decimal("180.00"),
            ),
            (
                Decimal("2"),
                Decimal("100"),
                Decimal("0"),
                Decimal("10"),
                Decimal("220.00"),
            ),
            (
                Decimal("2"),
                Decimal("100"),
                Decimal("10"),
                Decimal("10"),
                Decimal("198.00"),
            ),
        ],
    )
    def test_multiple_line_calculation_cases(
        self,
        quantity: Decimal,
        unit_price: Decimal,
        discount_rate: Decimal,
        tax_rate: Decimal,
        expected_total: Decimal,
    ) -> None:
        result = calculate_line(
            quantity=quantity,
            unit_price=unit_price,
            discount_rate=discount_rate,
            tax_rate=tax_rate,
        )

        assert result["line_total"] == expected_total


class FakeQuotationItem:
    def __init__(
        self,
        subtotal: str,
        discount_amount: str,
        tax_amount: str,
        line_total: str,
    ) -> None:
        self.subtotal = Decimal(subtotal)
        self.discount_amount = Decimal(discount_amount)
        self.tax_amount = Decimal(tax_amount)
        self.line_total = Decimal(line_total)


class TestCalculateTotals:
    def test_calculates_totals_for_one_item(self) -> None:
        items = [
            FakeQuotationItem(
                subtotal="1000.00",
                discount_amount="100.00",
                tax_amount="162.00",
                line_total="1062.00",
            )
        ]

        result = calculate_totals(items)  # type: ignore[arg-type]

        assert result["subtotal"] == Decimal("1000.00")
        assert result["discount_amount"] == Decimal("100.00")
        assert result["tax_amount"] == Decimal("162.00")
        assert result["total_amount"] == Decimal("1062.00")

    def test_calculates_totals_for_multiple_items(self) -> None:
        items = [
            FakeQuotationItem(
                subtotal="1000.00",
                discount_amount="100.00",
                tax_amount="162.00",
                line_total="1062.00",
            ),
            FakeQuotationItem(
                subtotal="500.00",
                discount_amount="0.00",
                tax_amount="90.00",
                line_total="590.00",
            ),
        ]

        result = calculate_totals(items)  # type: ignore[arg-type]

        assert result["subtotal"] == Decimal("1500.00")
        assert result["discount_amount"] == Decimal("100.00")
        assert result["tax_amount"] == Decimal("252.00")
        assert result["total_amount"] == Decimal("1652.00")

    def test_returns_zero_totals_for_empty_items(self) -> None:
        result = calculate_totals([])

        assert result["subtotal"] == Decimal("0.00")
        assert result["discount_amount"] == Decimal("0.00")
        assert result["tax_amount"] == Decimal("0.00")
        assert result["total_amount"] == Decimal("0.00")


# ============================================================
# Quotation API tests
# ============================================================


def test_quotations_require_authentication(
    client: TestClient,
) -> None:
    response = client.get(QUOTATIONS_URL)

    assert response.status_code == 401


def test_create_quotation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    customer = create_test_customer(
        client=client,
        auth_headers=auth_headers,
    )

    product = create_test_product(
        client=client,
        auth_headers=auth_headers,
    )

    payload = build_quotation_payload(
        customer_id=customer["id"],
        product_id=product["id"],
    )

    response = client.post(
        QUOTATIONS_URL,
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["id"]
    assert data["organization_id"]
    assert data["customer_id"] == customer["id"]
    assert data["created_by"]
    assert data["quotation_number"].startswith("Q-2026-")
    assert data["status"] == "draft"
    assert data["currency"] == "USD"
    assert data["notes"] == "Sample quotation"
    assert data["terms"] == "Net 30 Days"

    assert Decimal(data["subtotal"]) == Decimal("1000.00")
    assert Decimal(data["discount_amount"]) == Decimal("100.00")
    assert Decimal(data["tax_amount"]) == Decimal("162.00")
    assert Decimal(data["total_amount"]) == Decimal("1062.00")

    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["product_id"] == product["id"]
    assert item["description"] == "AI Email Automation"
    assert Decimal(item["quantity"]) == Decimal("2.00")
    assert Decimal(item["unit_price"]) == Decimal("500.00")
    assert Decimal(item["line_total"]) == Decimal("1062.00")


def test_get_quotation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    quotation = create_test_quotation(
        client=client,
        auth_headers=auth_headers,
    )

    quotation_id = quotation["id"]

    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == quotation_id
    assert data["quotation_number"] == quotation["quotation_number"]
    assert data["status"] == "draft"
    assert Decimal(data["total_amount"]) == Decimal("1062.00")
    assert len(data["items"]) == 1


def test_list_quotations(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    quotation = create_test_quotation(
        client=client,
        auth_headers=auth_headers,
    )

    response = client.get(
        QUOTATIONS_URL,
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == quotation["id"]


def test_search_quotations(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    quotation = create_test_quotation(
        client=client,
        auth_headers=auth_headers,
    )

    response = client.get(
        QUOTATIONS_URL,
        params={"search": quotation["quotation_number"]},
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["id"] == quotation["id"]


def test_filter_quotations_by_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    quotation = create_test_quotation(
        client=client,
        auth_headers=auth_headers,
    )

    draft_response = client.get(
        QUOTATIONS_URL,
        params={"status": "draft"},
        headers=auth_headers,
    )

    assert draft_response.status_code == 200

    draft_data = draft_response.json()

    assert draft_data["total"] == 1
    assert draft_data["items"][0]["id"] == quotation["id"]

    sent_response = client.get(
        QUOTATIONS_URL,
        params={"status": "sent"},
        headers=auth_headers,
    )

    assert sent_response.status_code == 200
    assert sent_response.json()["total"] == 0


def test_update_quotation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    customer = create_test_customer(
        client=client,
        auth_headers=auth_headers,
    )

    product = create_test_product(
        client=client,
        auth_headers=auth_headers,
    )

    create_payload = build_quotation_payload(
        customer_id=customer["id"],
        product_id=product["id"],
    )

    create_response = client.post(
        QUOTATIONS_URL,
        json=create_payload,
        headers=auth_headers,
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    quotation_id = create_response.json()["id"]

    update_payload = build_quotation_payload(
        customer_id=customer["id"],
        product_id=product["id"],
    )

    update_payload["notes"] = "Updated quotation notes"
    update_payload["terms"] = "Payment due within 15 days"

    update_response = client.put(
        f"{QUOTATIONS_URL}/{quotation_id}",
        json=update_payload,
        headers=auth_headers,
    )

    assert update_response.status_code == 200, (
        update_response.text
    )

    data = update_response.json()

    assert data["id"] == quotation_id
    assert data["notes"] == "Updated quotation notes"
    assert data["terms"] == "Payment due within 15 days"
    assert Decimal(data["subtotal"]) == Decimal("1000.00")
    assert Decimal(data["discount_amount"]) == Decimal("100.00")
    assert Decimal(data["tax_amount"]) == Decimal("162.00")
    assert Decimal(data["total_amount"]) == Decimal("1062.00")
    assert len(data["items"]) == 1


def test_delete_quotation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    quotation = create_test_quotation(
        client=client,
        auth_headers=auth_headers,
    )

    quotation_id = quotation["id"]

    delete_response = client.delete(
        f"{QUOTATIONS_URL}/{quotation_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}",
        headers=auth_headers,
    )

    assert get_response.status_code == 404
    assert get_response.json() == {
        "detail": "Quotation not found",
    }


def test_quotation_not_found(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    missing_quotation_id = uuid.uuid4()

    response = client.get(
        f"{QUOTATIONS_URL}/{missing_quotation_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Quotation not found",
    }


def test_invalid_customer_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    product = create_test_product(
        client=client,
        auth_headers=auth_headers,
    )

    payload = build_quotation_payload(
        customer_id=str(uuid.uuid4()),
        product_id=product["id"],
    )

    response = client.post(
        QUOTATIONS_URL,
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Customer not found or does not belong "
            "to this organization"
        )
    }


def test_invalid_product_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    customer = create_test_customer(
        client=client,
        auth_headers=auth_headers,
    )

    payload = build_quotation_payload(
        customer_id=customer["id"],
        product_id=str(uuid.uuid4()),
    )

    response = client.post(
        QUOTATIONS_URL,
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "Product not found or does not belong "
            "to this organization"
        )
    }


def test_create_quotation_without_product_reference(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    customer = create_test_customer(
        client=client,
        auth_headers=auth_headers,
    )

    payload = build_quotation_payload(
        customer_id=customer["id"],
        product_id=None,
    )

    payload["items"][0]["description"] = (
        "Custom consulting service"
    )

    response = client.post(
        QUOTATIONS_URL,
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["items"][0]["product_id"] is None
    assert data["items"][0]["description"] == (
        "Custom consulting service"
    )
    assert Decimal(data["total_amount"]) == Decimal("1062.00")