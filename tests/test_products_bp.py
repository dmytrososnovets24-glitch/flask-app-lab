import io
import json
import os
import tempfile
import unittest

from app import app
from app.products import storage

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 200
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 200

VALID = {
    "name": "Monitor",
    "content": "Монітор 27 дюймів, IPS, 144 Гц.",
    "price": "299.99",
    "category": "Електроніка",
    "quantity": "7",
}

CONFIG_KEYS = ("TESTING", "WTF_CSRF_ENABLED", "PRODUCTS_DB_PATH", "PRODUCTS_UPLOAD_DIR",
               "SEED_PRODUCTS", "MAX_IMAGE_SIZE")


class ProductsTestBase(unittest.TestCase):
    csrf = False
    seed = False

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "data", "products.json")
        self.upload_dir = os.path.join(self._tmp.name, "uploads")
        self._old = {k: app.config.get(k) for k in CONFIG_KEYS}
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=self.csrf, PRODUCTS_DB_PATH=self.db_path,
                          PRODUCTS_UPLOAD_DIR=self.upload_dir, SEED_PRODUCTS=self.seed)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self._old)
        self._tmp.cleanup()

    # --- допоміжні методи ---
    def add(self, image=None, follow=False, **overrides):
        data = {**VALID, **overrides}
        if image is not None:
            data["image"] = image
        return self.client.post("/product/add", data=data, content_type="multipart/form-data",
                                follow_redirects=follow)

    def edit(self, product_id, image=None, follow=False, **overrides):
        data = {**VALID, **overrides}
        if image is not None:
            data["image"] = image
        return self.client.post(f"/product/{product_id}/edit", data=data,
                                content_type="multipart/form-data", follow_redirects=follow)

    def stored(self):
        with app.app_context():
            return storage.all_products()

    def uploaded_files(self):
        return os.listdir(self.upload_dir) if os.path.isdir(self.upload_dir) else []


class ProductsCreateTests(ProductsTestBase):
    def test_empty_list(self):
        response = self.client.get("/product/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Товарів поки немає".encode(), response.data)

    def test_add_form_renders(self):
        response = self.client.get("/product/add")
        self.assertEqual(response.status_code, 200)
        for name in (b'name="name"', b'name="content"', b'name="price"',
                     b'name="category"', b'name="quantity"', b'name="image"'):
            self.assertIn(name, response.data)
        self.assertIn(b'enctype="multipart/form-data"', response.data)
        self.assertIn(b'rows="5"', response.data)
        self.assertIn(b'cols="40"', response.data)

    def test_add_valid_redirects_to_detail_prg(self):
        response = self.add()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/product/1"))
        page = self.client.get("/product/1")
        self.assertIn("успішно додано".encode(), page.data)
        self.assertIn(b"Monitor", page.data)

    def test_add_sets_id_and_created_at_automatically(self):
        self.add()
        self.add(name="Keyboard")
        products = self.stored()
        self.assertEqual([p["id"] for p in products], [1, 2])
        for p in products:
            self.assertRegex(p["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
        self.assertEqual(products[0]["price"], 299.99)
        self.assertEqual(products[0]["quantity"], 7)
        self.assertIsNone(products[0]["image"])

    def test_data_saved_to_json_file_and_survives_restart(self):
        self.add()
        with open(self.db_path, encoding="utf-8") as fh:
            raw = fh.read()
        data = json.loads(raw)
        self.assertEqual(data["products"]["1"]["name"], "Monitor")
        self.assertEqual(data["products"]["1"]["id"], 1)
        self.assertIn("Монітор 27 дюймів", raw)  # кирилиця без \u-екранування
        # «перезапуск»: новий клієнт читає той самий файл
        new_client = app.test_client()
        self.assertIn(b"Monitor", new_client.get("/product/").data)

    def test_add_with_png_image(self):
        response = self.add(image=(io.BytesIO(PNG), "photo.PNG"))
        self.assertEqual(response.status_code, 302)
        product = self.stored()[0]
        self.assertRegex(product["image"], r"^uploads/[0-9a-f]{32}\.png$")
        self.assertEqual(self.uploaded_files(), [os.path.basename(product["image"])])

    def test_add_with_jpeg_image(self):
        for filename in ("a.jpg", "b.jpeg"):
            self.assertEqual(self.add(image=(io.BytesIO(JPEG), filename)).status_code, 302)
        self.assertEqual(len(self.uploaded_files()), 2)

    def test_uploaded_filename_is_not_user_controlled(self):
        self.add(image=(io.BytesIO(PNG), "../../evil name.png"))
        files = self.uploaded_files()
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0], r"^[0-9a-f]{32}\.png$")

    def assert_invalid(self, response, text):
        self.assertEqual(response.status_code, 200)
        self.assertIn(text.encode(), response.data)
        self.assertEqual(self.stored(), [])
        self.assertEqual(self.uploaded_files(), [])

    def test_name_too_short(self):
        self.assert_invalid(self.add(name="ab"), "від 3 до 100 символів")

    def test_name_required(self):
        self.assert_invalid(self.add(name=""), "Вкажіть назву")

    def test_content_required(self):
        self.assert_invalid(self.add(content=""), "Додайте опис")

    def test_price_must_be_positive(self):
        for bad in ("0", "-5", "-0.01"):
            with self.subTest(price=bad):
                self.assert_invalid(self.add(price=bad), "більшою за нуль")

    def test_price_max_two_decimals(self):
        self.assert_invalid(self.add(price="10.123"), "не більше двох знаків")

    def test_price_required_and_numeric(self):
        self.assertEqual(self.add(price="").status_code, 200)
        self.assertEqual(self.add(price="abc").status_code, 200)
        self.assertEqual(self.add(price="inf").status_code, 200)
        self.assertEqual(self.stored(), [])

    def test_price_accepts_one_and_two_decimals(self):
        self.assertEqual(self.add(price="10.5").status_code, 302)
        self.assertEqual(self.add(price="0.01").status_code, 302)
        self.assertEqual([p["price"] for p in self.stored()], [10.5, 0.01])

    def test_quantity_must_not_be_negative(self):
        self.assert_invalid(self.add(quantity="-1"), "не може бути від’ємною")

    def test_quantity_zero_is_valid(self):
        self.assertEqual(self.add(quantity="0").status_code, 302)

    def test_quantity_must_be_integer(self):
        self.assertEqual(self.add(quantity="2.5").status_code, 200)
        self.assertEqual(self.stored(), [])

    def test_category_must_be_from_list(self):
        self.assertEqual(self.add(category="Невідома").status_code, 200)
        self.assertEqual(self.stored(), [])

    def test_image_wrong_extension(self):
        self.assert_invalid(self.add(image=(io.BytesIO(b"GIF89a"), "anim.gif")), "Дозволені лише")

    def test_image_content_must_match_extension(self):
        self.assert_invalid(self.add(image=(io.BytesIO(b"<?php echo 1;"), "shell.png")),
                            "не відповідає його розширенню")
        self.assert_invalid(self.add(image=(io.BytesIO(PNG), "fake.jpg")), "не відповідає його розширенню")

    def test_image_too_large(self):
        app.config["MAX_IMAGE_SIZE"] = 100
        self.assert_invalid(self.add(image=(io.BytesIO(PNG), "big.png")), "завеликий")

    def test_invalid_submit_shows_error_flash(self):
        self.assertIn("виправте помилки".encode(), self.add(name="").data)


class ProductsReadTests(ProductsTestBase):
    def test_list_shows_all_fields(self):
        self.add(image=(io.BytesIO(PNG), "p.png"))
        page = self.client.get("/product/").data.decode()
        for text in ("Monitor", "Електроніка", "299.99", ">7<", "uploads/"):
            self.assertIn(text, page)
        self.assertRegex(page, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def test_list_sorted_by_id(self):
        self.add(name="Alpha")
        self.add(name="Bravo")
        page = self.client.get("/product/").data.decode()
        self.assertLess(page.index("Alpha"), page.index("Bravo"))

    def test_list_without_image_uses_placeholder(self):
        self.add()
        self.assertIn(b"no-image.svg", self.client.get("/product/").data)

    def test_detail_shows_full_info(self):
        self.add()
        page = self.client.get("/product/1").data.decode()
        for text in ("Monitor", "Монітор 27 дюймів", "299.99", "Електроніка", "7"):
            self.assertIn(text, page)

    def test_detail_with_missing_image_file_uses_placeholder(self):
        self.add(image=(io.BytesIO(PNG), "p.png"))
        for name in self.uploaded_files():
            os.remove(os.path.join(self.upload_dir, name))
        page = self.client.get("/product/1")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"no-image.svg", page.data)

    def test_detail_not_found(self):
        response = self.client.get("/product/999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("не знайдено".encode(), response.data)

    def test_non_integer_id_not_found(self):
        self.assertEqual(self.client.get("/product/abc").status_code, 404)

    def test_html_in_name_is_escaped(self):
        self.add(name="<script>alert(1)</script>")
        page = self.client.get("/product/").data
        self.assertNotIn(b"<script>alert(1)</script>", page)
        self.assertIn(b"&lt;script&gt;", page)


class ProductsUpdateTests(ProductsTestBase):
    def test_edit_form_prefilled(self):
        self.add()
        page = self.client.get("/product/1/edit").data.decode()
        for text in ('value="Monitor"', "Монітор 27 дюймів", 'value="299.99"', 'value="7"'):
            self.assertIn(text, page)

    def test_edit_updates_fields_but_keeps_id_and_created_at(self):
        self.add()
        before = self.stored()[0]
        response = self.edit(1, name="Monitor Pro", price="349.50", quantity="3", category="Інше")
        self.assertEqual(response.status_code, 302)
        after = self.stored()[0]
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(after["created_at"], before["created_at"])
        self.assertEqual((after["name"], after["price"], after["quantity"], after["category"]),
                         ("Monitor Pro", 349.5, 3, "Інше"))
        self.assertIn("збережено".encode(), self.client.get("/product/1").data)

    def test_edit_without_new_image_keeps_old_one(self):
        self.add(image=(io.BytesIO(PNG), "p.png"))
        old = self.stored()[0]["image"]
        self.edit(1, name="Renamed")
        self.assertEqual(self.stored()[0]["image"], old)
        self.assertEqual(len(self.uploaded_files()), 1)

    def test_edit_with_new_image_replaces_and_removes_old_file(self):
        self.add(image=(io.BytesIO(PNG), "p.png"))
        old = self.stored()[0]["image"]
        self.edit(1, image=(io.BytesIO(JPEG), "new.jpg"))
        new = self.stored()[0]["image"]
        self.assertNotEqual(old, new)
        self.assertTrue(new.endswith(".jpg"))
        self.assertEqual(self.uploaded_files(), [os.path.basename(new)])

    def test_edit_invalid_does_not_change_data(self):
        self.add()
        response = self.edit(1, name="x", price="-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.stored()[0]["name"], "Monitor")

    def test_edit_invalid_image_keeps_old_one(self):
        self.add(image=(io.BytesIO(PNG), "p.png"))
        old = self.stored()[0]["image"]
        response = self.edit(1, image=(io.BytesIO(b"nope"), "x.png"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.stored()[0]["image"], old)

    def test_edit_not_found(self):
        self.assertEqual(self.client.get("/product/42/edit").status_code, 404)
        self.assertEqual(self.edit(42).status_code, 404)


class ProductsDeleteTests(ProductsTestBase):
    def test_delete_removes_product_and_redirects(self):
        self.add()
        response = self.client.post("/product/1/delete")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/product/"))
        self.assertEqual(self.stored(), [])
        self.assertIn("видалено".encode(), self.client.get("/product/").data)
        self.assertEqual(self.client.get("/product/1").status_code, 404)

    def test_delete_removes_image_file(self):
        self.add(image=(io.BytesIO(PNG), "p.png"))
        self.assertEqual(len(self.uploaded_files()), 1)
        self.client.post("/product/1/delete")
        self.assertEqual(self.uploaded_files(), [])

    def test_delete_only_selected_product(self):
        self.add(name="First")
        self.add(name="Second")
        self.client.post("/product/1/delete")
        self.assertEqual([p["name"] for p in self.stored()], ["Second"])

    def test_delete_requires_post(self):
        self.add()
        self.assertEqual(self.client.get("/product/1/delete").status_code, 405)
        self.assertEqual(len(self.stored()), 1)

    def test_delete_not_found(self):
        self.assertEqual(self.client.post("/product/77/delete").status_code, 404)

    def test_ids_are_unique_after_delete(self):
        self.add(name="One")
        self.add(name="Two")
        self.client.post("/product/1/delete")
        self.add(name="Three")
        self.assertEqual([(p["id"], p["name"]) for p in self.stored()], [(2, "Two"), (3, "Three")])

    def test_delete_buttons_have_confirmation(self):
        self.add()
        self.assertIn(b"confirm(", self.client.get("/product/").data)
        self.assertIn(b"confirm(", self.client.get("/product/1").data)


class ProductsCsrfTests(ProductsTestBase):
    csrf = True

    def test_add_without_token_rejected(self):
        response = self.add()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CSRF", response.data)
        self.assertEqual(self.stored(), [])

    def test_delete_without_token_rejected(self):
        app.config["WTF_CSRF_ENABLED"] = False
        self.add()
        app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post("/product/1/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.stored()), 1)
        self.assertIn("форма недійсна".encode(), response.data)

    def test_forms_contain_csrf_token(self):
        self.assertIn(b'name="csrf_token"', self.client.get("/product/add").data)


class ProductsSeedTests(ProductsTestBase):
    seed = True

    def test_fresh_storage_is_seeded(self):
        names = [p["name"] for p in self.stored()]
        self.assertEqual(names, ["Laptop", "Phone", "PC"])
        self.assertEqual(self.client.get("/product/1").status_code, 200)

    def test_seed_runs_only_once(self):
        self.stored()
        self.client.post("/product/1/delete")
        self.assertEqual([p["name"] for p in self.stored()], ["Phone", "PC"])


if __name__ == "__main__":
    unittest.main()
