import unittest

from app import app


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def login(self, username="admin", password="12345", follow=True):
        return self.client.post("/users/login",
                                data={"username": username, "password": password},
                                follow_redirects=follow)

    def test_login_page_opens(self):
        response = self.client.get("/users/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="username"', response.data)
        self.assertIn(b'name="password"', response.data)

    def test_profile_requires_login(self):
        response = self.client.get("/users/profile")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login", response.headers["Location"])

    def test_profile_redirect_shows_flash(self):
        response = self.client.get("/users/profile", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("потрібно увійти".encode(), response.data)

    def test_login_success(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Вхід виконано успішно".encode(), response.data)
        self.assertIn("Привіт, admin".encode(), response.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user"], "admin")

    def test_login_wrong_password(self):
        response = self.login(password="wrong")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Неправильне".encode(), response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)

    def test_logout(self):
        self.login()
        response = self.client.post("/users/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Ви вийшли".encode(), response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)
        self.assertEqual(self.client.get("/users/profile").status_code, 302)


class CookiesAndThemeTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.client.post("/users/login", data={"username": "admin", "password": "12345"})

    def test_add_cookie_shows_in_table(self):
        response = self.client.post("/users/cookies/add",
                                    data={"key": "color", "value": "red", "max_age": "600"},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Кукі «color» додано".encode(), response.data)
        self.assertIn(b"<td>color</td>", response.data)
        self.assertIn(b"red", response.data)

    def test_add_cookie_invalid_key(self):
        response = self.client.post("/users/cookies/add",
                                    data={"key": "bad key;", "value": "x", "max_age": "60"},
                                    follow_redirects=True)
        self.assertIn("Ключ кукі може містити".encode(), response.data)

    def test_add_cookie_invalid_max_age(self):
        response = self.client.post("/users/cookies/add",
                                    data={"key": "k", "value": "x", "max_age": "-5"},
                                    follow_redirects=True)
        self.assertIn("Термін дії".encode(), response.data)

    def test_cannot_overwrite_session_cookie(self):
        response = self.client.post("/users/cookies/add",
                                    data={"key": "session", "value": "x", "max_age": "60"},
                                    follow_redirects=True)
        self.assertIn("службове".encode(), response.data)

    def test_delete_cookie(self):
        self.client.post("/users/cookies/add", data={"key": "tmp", "value": "1", "max_age": "600"})
        response = self.client.post("/users/cookies/delete", data={"key": "tmp"},
                                    follow_redirects=True)
        self.assertIn("Кукі «tmp» видалено".encode(), response.data)
        self.assertNotIn(b"<td>tmp</td>", response.data)

    def test_delete_missing_cookie(self):
        response = self.client.post("/users/cookies/delete", data={"key": "nope"},
                                    follow_redirects=True)
        self.assertIn("не знайдено".encode(), response.data)

    def test_delete_all_keeps_session(self):
        self.client.post("/users/cookies/add", data={"key": "a", "value": "1", "max_age": "600"})
        self.client.post("/users/cookies/add", data={"key": "b", "value": "2", "max_age": "600"})
        response = self.client.post("/users/cookies/delete-all", follow_redirects=True)
        self.assertIn("Видалено кукі".encode(), response.data)
        self.assertNotIn(b"<td>a</td>", response.data)
        self.assertNotIn(b"<td>b</td>", response.data)
        self.assertIn("Привіт, admin".encode(), response.data)

    def test_theme_default_is_light(self):
        response = self.client.get("/users/profile")
        self.assertIn(b"theme-light", response.data)

    def test_theme_dark_is_saved(self):
        response = self.client.get("/users/theme/dark", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"theme-dark", response.data)
        # вибір зберігається для наступних відвідувань
        again = self.client.get("/users/profile")
        self.assertIn(b"theme-dark", again.data)

    def test_theme_can_switch_back(self):
        self.client.get("/users/theme/dark")
        response = self.client.get("/users/theme/light", follow_redirects=True)
        self.assertIn(b"theme-light", response.data)

    def test_unknown_theme(self):
        response = self.client.get("/users/theme/pink", follow_redirects=True)
        self.assertIn("Невідома кольорова схема".encode(), response.data)
        self.assertIn(b"theme-light", response.data)


if __name__ == "__main__":
    unittest.main()
