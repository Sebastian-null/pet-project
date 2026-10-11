def test_catalogue_lists_active_products(client):
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    slugs = {product["slug"] for product in response.json()}
    assert slugs == {"everyday-cotton", "soft-modal"}


def test_product_page_returns_variants(client):
    response = client.get("/api/v1/products/everyday-cotton")
    assert response.status_code == 200
    assert {variant["sku"] for variant in response.json()["variants"]} == {"EDC-BLK-M", "EDC-BLK-L"}


def test_unknown_product_is_404(client):
    assert client.get("/api/v1/products/does-not-exist").status_code == 404


def test_search_matches_name(client):
    response = client.get("/api/v1/products", params={"q": "modal"})
    assert [product["slug"] for product in response.json()] == ["soft-modal"]


def test_filters_narrow_by_colour_and_price(client):
    by_colour = client.get("/api/v1/products", params={"color": "Blue"}).json()
    assert [product["slug"] for product in by_colour] == ["soft-modal"]

    cheap = client.get("/api/v1/products", params={"max_price": 600}).json()
    assert [product["slug"] for product in cheap] == ["everyday-cotton"]


def test_filter_options_are_offered(client):
    options = client.get("/api/v1/products/filters").json()
    assert options["sizes"] == ["L", "M"]
    assert set(options["colors"]) == {"Black", "Blue"}
    assert set(options["categories"]) == {"briefs", "bra"}


def test_catalogue_can_be_split_by_range(client):
    womens = client.get("/api/v1/products", params={"gender": "women"}).json()
    assert [product["slug"] for product in womens] == ["soft-modal"]

    mens = client.get("/api/v1/products", params={"gender": "men"}).json()
    assert [product["slug"] for product in mens] == ["everyday-cotton"]


def test_catalogue_can_be_filtered_by_category(client):
    bras = client.get("/api/v1/products", params={"category": "bra"}).json()
    assert [product["slug"] for product in bras] == ["soft-modal"]


def test_unknown_range_is_rejected(client):
    assert client.get("/api/v1/products", params={"gender": "aliens"}).status_code == 422


def test_hidden_products_drop_out_of_the_filter_options(client, db_session):
    from app.models import Product
    with db_session() as session:
        session.query(Product).filter(Product.slug == "soft-modal").update({Product.is_active: False})
        session.commit()

    options = client.get("/api/v1/products/filters").json()
    assert options["categories"] == ["briefs"]
    assert "Blue" not in options["colors"]
