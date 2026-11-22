import unittest

from flask_login import current_user

from app import create_app, db
from app.users.models import User

PASSWORD = "secret123"
NEW_USER = {
    "username": "olena_k",
    "email": "olena@example.com",
    "password": "olena-pass",
    "confirm_password": "olena-pass",
}


class AuthTestBase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
        self.add_user("dmytro", "dmytro@example.com", PASSWORD)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def add_user(self, username, email, password, hashed=True):
        with self.app.app_context():
            user = User(username=username, email=email, password=password)
            if hashed:
                user.hash_password()
            db.session.add(user)
            db.session.commit()
            return user.id

    def get_user(self, **filters):
        with self.app.app_context():
            return db.session.scalar(db.select(User).filter_by(**filters))

    def register(self, follow=False, **overrides):
        return self.client.post("/users/register", data={**NEW_USER, **overrides},
                                follow_redirects=follow)

    def login(self, email="dmytro@example.com", password=PASSWORD, follow=False, **extra):
        return self.client.post("/users/login", data={"email": email, "password": password, **extra},
                                follow_redirects=follow)


class ViewsTests(AuthTestBase):
    """Сторінки реєстрації та входу завантажуються коректно."""

    def test_register_page_loads(self):
        response = self.client.get("/users/register")
        self.assertEqual(response.status_code, 200)
        page = response.data.decode()
        for name in ("username", "email", "password", "confirm_password"):
            self.assertIn(f'name="{name}"', page)
        self.assertIn("Зареєструватися", page)

    def test_login_page_loads(self):
        response = self.client.get("/users/login")
        self.assertEqual(response.status_code, 200)
        page = response.data.decode()
        for name in ("email", "password", "remember"):
            self.assertIn(f'name="{name}"', page)
        self.assertIn('type="password"', page)

    def test_menu_for_guest(self):
        page = self.client.get("/").data.decode()
        self.assertIn('href="/users/login"', page)
        self.assertIn('href="/users/register"', page)
        self.assertNotIn('href="/users/logout"', page)
        self.assertNotIn('href="/users/account"', page)


class RegistrationTests(AuthTestBase):
    """Збереження користувача в БД під час реєстрації."""

    def test_registration_saves_user_with_hashed_password(self):
        response = self.register()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/users/login"))
        user = self.get_user(username="olena_k")
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "olena@example.com")
        self.assertNotEqual(user.password, "olena-pass")  # у БД лише хеш
        self.assertTrue(user.password.startswith("$2b$"))
        with self.app.app_context():
            self.assertTrue(user.check_password("olena-pass"))
            self.assertFalse(user.check_password("wrong"))

    def test_registration_shows_success_message(self):
        response = self.register(follow=True)
        self.assertIn("Обліковий запис для olena_k створено".encode(), response.data)

    def test_email_is_normalized(self):
        self.register(email="  Olena@Example.COM ")
        self.assertIsNotNone(self.get_user(email="olena@example.com"))

    def assert_not_registered(self, response, message):
        self.assertEqual(response.status_code, 200)
        self.assertIn(message.encode(), response.data)
        self.assertIsNone(self.get_user(username=NEW_USER["username"]))

    def test_existing_email_is_rejected(self):
        response = self.register(email="dmytro@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Користувач з email dmytro@example.com уже існує".encode(), response.data)
        self.assertIsNone(self.get_user(username="olena_k"))

    def test_existing_username_is_rejected(self):
        response = self.register(username="dmytro")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Користувач з ім&#39;ям dmytro уже існує".encode(), response.data)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(User.id))), 1)

    def test_invalid_email_is_rejected(self):
        self.assert_not_registered(self.register(email="not-an-email"), "коректну адресу")

    def test_username_length(self):
        self.assert_not_registered(self.register(username="abc"), "від 4 до 14 символів")
        self.assert_not_registered(self.register(username="a" * 15), "від 4 до 14 символів")

    def test_username_characters(self):
        self.assert_not_registered(self.register(username="1olena"), "латинської літери")
        self.assertIsNone(self.get_user(username="ol ena"))
        self.register(username="ol ena")
        self.assertIsNone(self.get_user(username="ol ena"))

    def test_password_too_short(self):
        self.assert_not_registered(self.register(password="12345", confirm_password="12345"),
                                   "щонайменше 6 символів")

    def test_passwords_must_match(self):
        self.assert_not_registered(self.register(confirm_password="other-pass"), "Паролі не збігаються")

    def test_required_fields(self):
        response = self.register(username="", email="", password="", confirm_password="")
        page = response.data.decode()
        for text in ("Вкажіть ім&#39;я користувача", "Вкажіть електронну пошту", "Вкажіть пароль",
                     "Повторіть пароль"):
            self.assertIn(text, page)

    def test_authenticated_user_is_redirected_from_register(self):
        self.login()
        response = self.client.get("/users/register")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/users/account"))


class LoginLogoutTests(AuthTestBase):
    """Вхід і вихід користувача на сайті."""

    def test_login_success_redirects_to_account(self):
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/users/account"))
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["_user_id"], "1")  # login_user зберігає id рядком

    def test_current_user_after_login(self):
        with self.client:
            self.login()
            self.client.get("/users/account")
            self.assertTrue(current_user.is_authenticated)
            self.assertEqual(current_user.username, "dmytro")

    def test_account_shows_user_data(self):
        page = self.login(follow=True).data.decode()
        self.assertIn("Вітаємо, dmytro! Вхід виконано успішно.", page)
        self.assertIn("Вітаємо, dmytro!", page)
        self.assertIn("dmytro@example.com", page)

    def test_menu_for_signed_in_user(self):
        page = self.login(follow=True).data.decode()
        self.assertIn('href="/users/account"', page)
        self.assertIn('href="/users/logout"', page)
        self.assertIn("Вихід", page)
        self.assertNotIn('href="/users/register"', page)
        self.assertNotIn('href="/users/login"', page)

    def test_wrong_password(self):
        response = self.login(password="wrong-pass", follow=True)
        self.assertIn("Неправильний email або пароль".encode(), response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("_user_id", sess)

    def test_unknown_email(self):
        response = self.login(email="nobody@example.com", follow=True)
        self.assertIn("Неправильний email або пароль".encode(), response.data)

    def test_user_with_plain_password_cannot_login(self):
        self.add_user("legacy", "legacy@example.com", "pass1", hashed=False)
        response = self.login(email="legacy@example.com", password="pass1", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Неправильний email або пароль".encode(), response.data)

    def test_remember_me_sets_cookie(self):
        response = self.login(remember="y")
        cookies = response.headers.getlist("Set-Cookie")
        self.assertTrue(any(c.startswith("remember_token=") for c in cookies))

    def test_without_remember_me_no_cookie(self):
        cookies = self.login().headers.getlist("Set-Cookie")
        self.assertFalse(any(c.startswith("remember_token=") for c in cookies))

    def test_authenticated_user_is_redirected_from_login(self):
        self.login()
        response = self.client.get("/users/login")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/users/account"))

    def test_logout(self):
        self.login()
        response = self.client.get("/users/logout", follow_redirects=True)
        self.assertIn("Ви вийшли з системи".encode(), response.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("_user_id", sess)
        self.assertEqual(self.client.get("/users/account").status_code, 302)

    def test_registered_user_can_login(self):
        self.register()
        response = self.login(email="olena@example.com", password="olena-pass", follow=True)
        self.assertIn("Вітаємо, olena_k!".encode(), response.data)

    def test_login_follows_safe_next(self):
        response = self.client.post("/users/login?next=/users/",
                                    data={"email": "dmytro@example.com", "password": PASSWORD})
        self.assertTrue(response.headers["Location"].endswith("/users/"))

    def test_login_ignores_external_next(self):
        response = self.client.post("/users/login?next=https://evil.example.com/",
                                    data={"email": "dmytro@example.com", "password": PASSWORD})
        self.assertTrue(response.headers["Location"].endswith("/users/account"))


class ProtectedPagesTests(AuthTestBase):
    """@login_required: профіль і список користувачів лише для авторизованих."""

    def test_pages_redirect_guest_to_login(self):
        for url in ("/users/account", "/users/", "/users/profile"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn("/users/login?next=", response.headers["Location"])

    def test_redirect_shows_message(self):
        response = self.client.get("/users/account", follow_redirects=True)
        self.assertIn("Будь ласка, увійдіть, щоб отримати доступ до цієї сторінки".encode(), response.data)
        self.assertIn(b"alert-warning", response.data)

    def test_users_list_with_count(self):
        self.add_user("andrii", "andrii@example.com", PASSWORD)
        self.login()
        page = self.client.get("/users/").data.decode()
        self.assertIn("Список користувачів (2)", page)
        self.assertIn("dmytro@example.com", page)
        self.assertIn("andrii@example.com", page)

    def test_users_list_empty_message(self):
        with self.app.test_request_context():
            from flask import render_template
            html = render_template("users/users.html", title="Користувачі", users=[])
        self.assertIn("Зареєстрованих користувачів поки немає", html)
        self.assertIn("Список користувачів (0)", html)

    def test_new_post_author_defaults_to_current_user(self):
        self.add_user("andrii", "andrii@example.com", PASSWORD)
        self.login(email="andrii@example.com")
        page = self.client.get("/post/create").data.decode()
        self.assertIn('<option selected value="2">andrii</option>', page)


class CsrfTests(AuthTestBase):
    def setUp(self):
        super().setUp()
        self.app.config["WTF_CSRF_ENABLED"] = True

    def test_forms_contain_csrf_token(self):
        for url in ("/users/register", "/users/login"):
            self.assertIn(b'name="csrf_token"', self.client.get(url).data)

    def test_register_without_token_is_rejected(self):
        self.assertEqual(self.register().status_code, 200)
        self.assertIsNone(self.get_user(username="olena_k"))

    def test_login_without_token_is_rejected(self):
        self.login()
        with self.client.session_transaction() as sess:
            self.assertNotIn("_user_id", sess)


if __name__ == "__main__":
    unittest.main()
