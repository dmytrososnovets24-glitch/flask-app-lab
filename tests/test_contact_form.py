import os
import tempfile
import unittest

from app import app

VALID = {
    "name": "Dmytro",
    "email": "dmytro@example.com",
    "phone": "+380501234567",
    "subject": "question",
    "message": "Доброго дня! Це тестове повідомлення.",
}


class ContactFormTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.log_path = os.path.join(self._tmp.name, "logs", "contact.log")
        self._old = {k: app.config.get(k) for k in ("TESTING", "WTF_CSRF_ENABLED", "CONTACT_LOG_FILE")}
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, CONTACT_LOG_FILE=self.log_path)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self._old)
        # закриваємо файл логу перед видаленням тимчасової теки (Windows)
        import logging
        logger = logging.getLogger(f"contact_form.{self.log_path}")
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        from app import contact_log
        contact_log._handlers.pop(self.log_path, None)
        self._tmp.cleanup()

    def post(self, **overrides):
        data = {**VALID, **overrides}
        return self.client.post("/contacts", data=data)

    def read_log(self):
        if not os.path.exists(self.log_path):
            return ""
        with open(self.log_path, encoding="utf-8") as fh:
            return fh.read()

    def test_form_renders_all_fields(self):
        response = self.client.get("/contacts")
        self.assertEqual(response.status_code, 200)
        for field in (b'name="name"', b'name="email"', b'name="phone"',
                      b'name="subject"', b'name="message"', b'type="submit"'):
            self.assertIn(field, response.data)
        self.assertIn(b"<select", response.data)
        self.assertIn(b"<textarea", response.data)

    def test_valid_post_redirects_logs_and_flashes(self):
        response = self.post()
        # Post/Redirect/Get
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/contacts"))
        log = self.read_log()
        self.assertIn("name=Dmytro", log)
        self.assertIn("email=dmytro@example.com", log)
        self.assertIn("phone=+380501234567", log)
        self.assertIn("subject=Запитання", log)
        self.assertIn("Це тестове повідомлення", log)

        page = self.client.get("/contacts")
        self.assertIn("надіслано та збережено".encode(), page.data)
        # повторне оновлення сторінки не відправляє форму вдруге
        self.client.get("/contacts")
        self.assertEqual(len(self.read_log().strip().splitlines()), 1)

    def test_log_appends_each_submission(self):
        self.post(name="Anna1")
        self.post(name="Oleksa")
        lines = self.read_log().strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("name=Anna1", lines[0])
        self.assertIn("name=Oleksa", lines[1])

    def test_multiline_message_is_single_log_line(self):
        self.post(message="рядок 1\nрядок 2\n\nрядок 3")
        self.assertEqual(len(self.read_log().strip().splitlines()), 1)

    def assert_rejected(self, response, text):
        self.assertEqual(response.status_code, 200)
        self.assertIn(text.encode(), response.data)
        self.assertEqual(self.read_log(), "")

    def test_name_too_short(self):
        self.assert_rejected(self.post(name="Ann"), "від 4 до 10 символів")

    def test_name_too_long(self):
        self.assert_rejected(self.post(name="A" * 11), "від 4 до 10 символів")

    def test_name_boundaries_are_valid(self):
        self.assertEqual(self.post(name="A" * 4).status_code, 302)
        self.assertEqual(self.post(name="B" * 10).status_code, 302)

    def test_invalid_email(self):
        self.assert_rejected(self.post(email="not-an-email"), "коректну адресу")

    def test_phone_wrong_format(self):
        for bad in ("0501234567", "+38050123456", "+3805012345678", "+380abcdefghi", "+381501234567"):
            with self.subTest(phone=bad):
                self.assert_rejected(self.post(phone=bad), "Формат телефону")

    def test_subject_required(self):
        self.assert_rejected(self.post(subject=""), "Оберіть тему")

    def test_subject_must_be_from_list(self):
        response = self.post(subject="hacker")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.read_log(), "")

    def test_message_required(self):
        self.assert_rejected(self.post(message=""), "Напишіть повідомлення")

    def test_message_too_long(self):
        self.assert_rejected(self.post(message="x" * 501), "не більше 500 символів")

    def test_message_500_is_valid(self):
        self.assertEqual(self.post(message="x" * 500).status_code, 302)

    def test_error_flash_shown_on_invalid_submit(self):
        response = self.post(name="")
        self.assertIn("виправте помилки".encode(), response.data)

    def test_log_failure_flashes_error(self):
        app.config["CONTACT_LOG_FILE"] = os.path.join(self._tmp.name, "blocked.txt", "x.log")
        # робимо з "blocked.txt" файл, щоб створити каталог всередині було неможливо
        with open(os.path.join(self._tmp.name, "blocked.txt"), "w") as fh:
            fh.write("file")
        with self.assertLogs(app.logger, level="ERROR"):
            response = self.client.post("/contacts", data=VALID, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Не вдалося зберегти".encode(), response.data)


class ContactCsrfTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.log_path = os.path.join(self._tmp.name, "contact.log")
        self._old = {k: app.config.get(k) for k in ("TESTING", "WTF_CSRF_ENABLED", "CONTACT_LOG_FILE")}
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=True, CONTACT_LOG_FILE=self.log_path)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self._old)
        self._tmp.cleanup()

    def test_form_contains_csrf_token(self):
        response = self.client.get("/contacts")
        self.assertIn(b'name="csrf_token"', response.data)

    def test_post_without_token_is_rejected(self):
        response = self.client.post("/contacts", data=VALID)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(os.path.exists(self.log_path))
        self.assertIn("CSRF".encode(), response.data)


if __name__ == "__main__":
    unittest.main()
