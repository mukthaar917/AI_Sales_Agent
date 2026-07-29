import uuid
from decimal import Decimal


PRODUCTS_URL = "/api/v1/products"


def build_product_payload(
    sku: str = "LAP-001",
    name: str = "Business Laptop",
) -> dict:
    return {
        "sku": sku,
        "name": name,
        "description": "Dell Latitude business laptop",
        "unit": "pcs",
        "unit_price": 1200.00,
        "currency": "USD",
        "tax_rate": 18.00,
    }


def test_products_require_authentication(client):
    response = client.get(PRODUCTS_URL)

    assert response.status_code == 401


def test_create_product(client, auth_headers):
    response = client.post(
        PRODUCTS_URL,
        json=build_product_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["sku"] == "LAP-001"
    assert data["name"] == "Business Laptop"
    assert Decimal(data["unit_price"]) == Decimal("1200.00")
    assert data["currency"] == "USD"
    assert Decimal(data["tax_rate"]) == Decimal("18.00")
    assert data["is_active"] is True
    assert data["id"]
    assert data["organization_id"]


def test_product_crud_lifecycle(client, auth_headers):
    create_response = client.post(
        PRODUCTS_URL,
        json=build_product_payload(
            sku="MON-001",
            name="Business Monitor",
        ),
        headers=auth_headers,
    )

    assert create_response.status_code == 201

    created_product = create_response.json()
    product_id = created_product["id"]

    get_response = client.get(
        f"{PRODUCTS_URL}/{product_id}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["sku"] == "MON-001"

    update_response = client.put(
        f"{PRODUCTS_URL}/{product_id}",
        json={
            "name": "Business Monitor Pro",
            "unit_price": 1450.00,
        },
        headers=auth_headers,
    )

    assert update_response.status_code == 200

    updated_product = update_response.json()

    assert updated_product["name"] == "Business Monitor Pro"
    assert Decimal(updated_product["unit_price"]) == Decimal("1450.00")

    delete_response = client.delete(
        f"{PRODUCTS_URL}/{product_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    hidden_response = client.get(
        f"{PRODUCTS_URL}/{product_id}",
        headers=auth_headers,
    )

    assert hidden_response.status_code == 404

    inactive_response = client.get(
        f"{PRODUCTS_URL}/{product_id}",
        params={"include_inactive": True},
        headers=auth_headers,
    )

    assert inactive_response.status_code == 200
    assert inactive_response.json()["is_active"] is False


def test_list_and_search_products(client, auth_headers):
    products = [
        build_product_payload(
            sku="LAP-SEARCH-001",
            name="Latitude Laptop",
        ),
        build_product_payload(
            sku="MON-SEARCH-001",
            name="Office Monitor",
        ),
        build_product_payload(
            sku="KEY-SEARCH-001",
            name="Mechanical Keyboard",
        ),
    ]

    for product in products:
        response = client.post(
            PRODUCTS_URL,
            json=product,
            headers=auth_headers,
        )

        assert response.status_code == 201

    list_response = client.get(
        PRODUCTS_URL,
        headers=auth_headers,
    )

    assert list_response.status_code == 200

    list_data = list_response.json()

    assert list_data["total"] == 3
    assert list_data["page"] == 1
    assert list_data["page_size"] == 20
    assert len(list_data["items"]) == 3

    sku_search_response = client.get(
        PRODUCTS_URL,
        params={"search": "MON-SEARCH"},
        headers=auth_headers,
    )

    assert sku_search_response.status_code == 200

    sku_search_data = sku_search_response.json()

    assert sku_search_data["total"] == 1
    assert sku_search_data["items"][0]["sku"] == "MON-SEARCH-001"

    name_search_response = client.get(
        PRODUCTS_URL,
        params={"search": "keyboard"},
        headers=auth_headers,
    )

    assert name_search_response.status_code == 200

    name_search_data = name_search_response.json()

    assert name_search_data["total"] == 1
    assert name_search_data["items"][0]["name"] == "Mechanical Keyboard"


def test_deleted_product_is_hidden_from_default_list(
    client,
    auth_headers,
):
    create_response = client.post(
        PRODUCTS_URL,
        json=build_product_payload(
            sku="DEL-001",
            name="Deleted Product",
        ),
        headers=auth_headers,
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    delete_response = client.delete(
        f"{PRODUCTS_URL}/{product_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 204

    default_list_response = client.get(
        PRODUCTS_URL,
        headers=auth_headers,
    )

    assert default_list_response.status_code == 200
    assert default_list_response.json()["total"] == 0

    inactive_list_response = client.get(
        PRODUCTS_URL,
        params={"include_inactive": True},
        headers=auth_headers,
    )

    assert inactive_list_response.status_code == 200

    inactive_list_data = inactive_list_response.json()

    assert inactive_list_data["total"] == 1
    assert inactive_list_data["items"][0]["is_active"] is False


def test_product_not_found(client, auth_headers):
    missing_product_id = uuid.uuid4()

    response = client.get(
        f"{PRODUCTS_URL}/{missing_product_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Product not found",
    }


def test_duplicate_product_sku_returns_conflict(
    client,
    auth_headers,
):
    payload = build_product_payload(
        sku="DUP-001",
        name="Original Product",
    )

    first_response = client.post(
        PRODUCTS_URL,
        json=payload,
        headers=auth_headers,
    )

    assert first_response.status_code == 201

    duplicate_payload = build_product_payload(
        sku="DUP-001",
        name="Duplicate Product",
    )

    duplicate_response = client.post(
        PRODUCTS_URL,
        json=duplicate_payload,
        headers=auth_headers,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "A product with this SKU already exists",
    }