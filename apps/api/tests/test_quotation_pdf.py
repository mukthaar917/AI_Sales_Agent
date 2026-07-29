import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient


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
        "company_name": f"PDF Test Company {unique_value}",
        "contact_name": "PDF Test Customer",
        "email": f"pdf-customer-{unique_value}@example.com",
        "phone": "+1-555-123-4567",
        "website": "https://example.com",
        "address": "123 Main Street",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "postal_code": "10001",
        "tax_number": f"TAX-{unique_value}",
        "notes": "Quotation PDF test customer",
    }


def build_product_payload() -> dict:
    """Build a valid product request body."""
    unique_value = uuid.uuid4().hex[:12]

    return {
        "sku": f"PDF-{unique_value}",
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
    """Create and return a customer through the API."""
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
    """Create and return a product through the API."""
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
    today = date.today()

    return {
        "customer_id": customer_id,
        "issue_date": today.isoformat(),
        "expiry_date": (today + timedelta(days=30)).isoformat(),
        "currency": "USD",
        "notes": "Thank you for your business.",
        "terms": "Payment is due within 30 days.",
        "items": [
            {
                "product_id": product_id,
                "description": "PDF quotation test item",
                "quantity": 2.00,
                "unit": "License",
                "unit_price": 125.50,
                "discount_rate": 10.00,
                "tax_rate": 8.00,
                "sort_order": 1,
            }
        ],
    }


def create_test_quotation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> dict:
    """Create the customer, product, and quotation required by a test."""
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


@pytest.fixture()
def quotation_id(
    client: TestClient,
    auth_headers: dict[str, str],
) -> str:
    """Create a quotation and return its ID."""
    quotation = create_test_quotation(
        client=client,
        auth_headers=auth_headers,
    )

    assert quotation.get("id")

    return quotation["id"]


# ============================================================
# Authentication and basic PDF tests
# ============================================================


def test_download_quotation_pdf_requires_authentication(
    client: TestClient,
) -> None:
    quotation_id = uuid.uuid4()

    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}/pdf",
    )

    assert response.status_code == 401


def test_download_quotation_pdf_returns_pdf(
    client: TestClient,
    auth_headers: dict[str, str],
    quotation_id: str,
) -> None:
    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 100


def test_download_quotation_pdf_has_attachment_header(
    client: TestClient,
    auth_headers: dict[str, str],
    quotation_id: str,
) -> None:
    quotation_response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}",
        headers=auth_headers,
    )

    assert quotation_response.status_code == 200, (
        quotation_response.text
    )

    quotation_number = quotation_response.json()[
        "quotation_number"
    ]

    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text

    content_disposition = response.headers.get(
        "content-disposition"
    )

    assert content_disposition is not None
    assert "attachment" in content_disposition.lower()
    assert f"{quotation_number}.pdf" in content_disposition


def test_download_quotation_pdf_has_content_length(
    client: TestClient,
    auth_headers: dict[str, str],
    quotation_id: str,
) -> None:
    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text

    content_length = response.headers.get("content-length")

    assert content_length is not None
    assert int(content_length) == len(response.content)


def test_download_missing_quotation_pdf_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    missing_quotation_id = uuid.uuid4()

    response = client.get(
        f"{QUOTATIONS_URL}/{missing_quotation_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Quotation not found",
    }


# ============================================================
# Quotation item PDF tests
# ============================================================


def test_download_quotation_pdf_with_manual_item(
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
        "Custom service without product reference"
    )

    create_response = client.post(
        QUOTATIONS_URL,
        json=payload,
        headers=auth_headers,
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    quotation_id = create_response.json()["id"]

    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 100


def test_download_quotation_pdf_with_multiple_items(
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

    payload["items"].append(
        {
            "product_id": None,
            "description": (
                "Additional custom implementation service"
            ),
            "quantity": 5.00,
            "unit": "Hour",
            "unit_price": 75.00,
            "discount_rate": 0.00,
            "tax_rate": 8.00,
            "sort_order": 2,
        }
    )

    create_response = client.post(
        QUOTATIONS_URL,
        json=payload,
        headers=auth_headers,
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    quotation_id = create_response.json()["id"]

    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 100


# ============================================================
# PDF generation failure tests
# ============================================================


def test_download_quotation_pdf_generation_failure_returns_500(
    client: TestClient,
    auth_headers: dict[str, str],
    quotation_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_pdf_generator(*args, **kwargs) -> bytes:
        raise RuntimeError("Test PDF generation failure")

    monkeypatch.setattr(
        "app.api.v1.quotations.generate_quotation_pdf",
        failing_pdf_generator,
    )

    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to generate quotation PDF",
    }


def test_empty_generated_pdf_returns_500(
    client: TestClient,
    auth_headers: dict[str, str],
    quotation_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def empty_pdf_generator(*args, **kwargs) -> bytes:
        return b""

    monkeypatch.setattr(
        "app.api.v1.quotations.generate_quotation_pdf",
        empty_pdf_generator,
    )

    response = client.get(
        f"{QUOTATIONS_URL}/{quotation_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Generated quotation PDF is empty",
    }