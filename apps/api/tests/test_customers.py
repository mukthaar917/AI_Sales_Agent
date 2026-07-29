from fastapi.testclient import TestClient


CUSTOMER_PAYLOAD = {
    "company_name": "Acme Test Industries",
    "contact_name": "Jane Smith",
    "email": "jane.smith@example.com",
    "phone": "+1-555-0100",
    "website": "https://example.com",
    "address": "100 Test Street",
    "city": "Test City",
    "state": "California",
    "country": "United States",
    "postal_code": "90001",
    "tax_number": "TEST-TAX-100",
    "notes": "Created by automated test",
}


def test_customers_require_authentication(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/customers")

    assert response.status_code == 401


def test_create_customer(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/customers",
        json=CUSTOMER_PAYLOAD,
        headers=auth_headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["company_name"] == "Acme Test Industries"
    assert data["contact_name"] == "Jane Smith"
    assert data["email"] == "jane.smith@example.com"
    assert data["is_active"] is True
    assert data["id"]
    assert data["organization_id"]


def test_customer_crud_lifecycle(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    # Create
    create_response = client.post(
        "/api/v1/customers",
        json=CUSTOMER_PAYLOAD,
        headers=auth_headers,
    )

    assert create_response.status_code == 201

    customer_id = create_response.json()["id"]

    # Retrieve
    get_response = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == customer_id

    # Update
    update_response = client.put(
        f"/api/v1/customers/{customer_id}",
        json={
            "contact_name": "John Smith",
            "notes": "Customer updated by automated test",
        },
        headers=auth_headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["contact_name"] == "John Smith"
    assert (
        update_response.json()["notes"]
        == "Customer updated by automated test"
    )

    # Soft delete
    delete_response = client.delete(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    # Hidden by default after soft deletion
    hidden_response = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers,
    )

    assert hidden_response.status_code == 404

    # Available when inactive records are requested
    inactive_response = client.get(
        f"/api/v1/customers/{customer_id}",
        params={"include_inactive": True},
        headers=auth_headers,
    )

    assert inactive_response.status_code == 200
    assert inactive_response.json()["is_active"] is False


def test_list_and_search_customers(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    first_response = client.post(
        "/api/v1/customers",
        json={
            **CUSTOMER_PAYLOAD,
            "company_name": "Northwind Automation",
            "email": "northwind@example.com",
        },
        headers=auth_headers,
    )

    second_response = client.post(
        "/api/v1/customers",
        json={
            **CUSTOMER_PAYLOAD,
            "company_name": "Contoso Manufacturing",
            "email": "contoso@example.com",
        },
        headers=auth_headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get(
        "/api/v1/customers",
        params={
            "search": "Northwind",
            "page": 1,
            "page_size": 10,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) == 1
    assert data["items"][0]["company_name"] == "Northwind Automation"


def test_customer_not_found(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    missing_customer_id = "00000000-0000-0000-0000-000000000001"

    response = client.get(
        f"/api/v1/customers/{missing_customer_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"