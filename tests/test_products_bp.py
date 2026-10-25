import unittest

from app import app
from app.products.views import products


class ProductsBlueprintTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_product_list(self):
        """Сторінка /products/ показує всі товари."""
        response = self.client.get("/products/")
        self.assertEqual(response.status_code, 200)
        for product in products:
            self.assertIn(product["name"].encode(), response.data)

    def test_product_detail(self):
        """Сторінка /products/<id> показує опис і ціну товару."""
        response = self.client.get("/products/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Laptop", response.data)
        self.assertIn(b"1200", response.data)
        self.assertIn("Intel Core i7".encode(), response.data)

    def test_every_product_has_detail_page(self):
        for product in products:
            response = self.client.get(f"/products/{product['id']}")
            self.assertEqual(response.status_code, 200)
            self.assertIn(product["name"].encode(), response.data)

    def test_unknown_product_returns_404(self):
        response = self.client.get("/products/999")
        self.assertEqual(response.status_code, 404)

    def test_non_integer_id_returns_404(self):
        response = self.client.get("/products/abc")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
