import unittest
from datetime import datetime

from app import create_app, db
from app.posts.models import Post

VALID = {
    "title": "My first post",
    "content": "This is TDD!",
    "is_active": "y",
    "publish_date": "2026-11-10T09:30",
    "category": "tech",
}


class PostTestBase(unittest.TestCase):
    csrf = False

    def setUp(self):
        self.app = create_app("testing")
        self.app.config["WTF_CSRF_ENABLED"] = self.csrf
        self.client = self.app.test_client()
        # створення таблиць у тестовій базі (SQLite в пам'яті)
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        # очищення бази після кожного тесту
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # --- допоміжні методи ---
    def add_post(self, **fields):
        data = {"title": "Existing post", "content": "Some content", **fields}
        with self.app.app_context():
            post = Post(**data)
            db.session.add(post)
            db.session.commit()
            return post.id

    def get_post(self, post_id):
        with self.app.app_context():
            return db.session.get(Post, post_id)

    def all_posts(self):
        with self.app.app_context():
            return db.session.scalars(db.select(Post).order_by(Post.id)).all()

    def create(self, follow=False, **overrides):
        data = {**VALID, **overrides}
        data = {k: v for k, v in data.items() if v is not None}
        return self.client.post("/post/create", data=data, follow_redirects=follow)


class PostModelTests(PostTestBase):
    def test_defaults(self):
        post = self.get_post(self.add_post())
        self.assertEqual(post.category, "other")
        self.assertTrue(post.is_active)
        self.assertEqual(post.author, "Anonymous")
        self.assertIsInstance(post.posted, datetime)

    def test_repr(self):
        post = self.get_post(self.add_post(title="Hello"))
        self.assertIn("Hello", repr(post))
        self.assertIn("Post", repr(post))


class PostCreateTests(PostTestBase):
    def test_create_form_renders(self):
        response = self.client.get("/post/create")
        self.assertEqual(response.status_code, 200)
        for name in (b'name="title"', b'name="content"', b'name="is_active"',
                     b'name="publish_date"', b'name="category"', b'type="submit"'):
            self.assertIn(name, response.data)
        # автора у формі не обирають
        self.assertNotIn(b'name="author"', response.data)

    def test_create_post(self):
        response = self.create(follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Пост успішно додано".encode(), response.data)

        posts = self.all_posts()
        self.assertEqual(len(posts), 1)
        post = posts[0]
        self.assertEqual(post.title, "My first post")
        self.assertEqual(post.content, "This is TDD!")
        self.assertEqual(post.category, "tech")
        self.assertTrue(post.is_active)
        self.assertEqual(post.posted, datetime(2026, 11, 10, 9, 30))

    def test_create_redirects_to_list(self):
        response = self.create()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/post"))

    def test_author_is_anonymous_without_session(self):
        self.create()
        self.assertEqual(self.all_posts()[0].author, "Anonymous")

    def test_author_is_user_from_session(self):
        with self.client.session_transaction() as sess:
            sess["user"] = "admin"
        self.create()
        self.assertEqual(self.all_posts()[0].author, "admin")

    def test_unchecked_is_active_creates_hidden_post(self):
        self.create(is_active=None)
        self.assertFalse(self.all_posts()[0].is_active)

    def test_publish_date_defaults_to_now(self):
        before = datetime.now().replace(microsecond=0)
        self.create(publish_date=None)
        self.assertGreaterEqual(self.all_posts()[0].posted, before)

    def assert_rejected(self, response, text):
        self.assertEqual(response.status_code, 200)
        self.assertIn(text.encode(), response.data)
        self.assertEqual(self.all_posts(), [])

    def test_title_required(self):
        self.assert_rejected(self.create(title=""), "Вкажіть заголовок")

    def test_title_too_short(self):
        self.assert_rejected(self.create(title="a"), "від 2 до 150 символів")

    def test_title_too_long(self):
        self.assert_rejected(self.create(title="x" * 151), "від 2 до 150 символів")

    def test_content_required(self):
        self.assert_rejected(self.create(content=""), "Додайте текст поста")

    def test_category_must_be_from_list(self):
        response = self.create(category="science")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_posts(), [])

    def test_invalid_submit_shows_flash(self):
        self.assertIn("Перевірте дані у формі".encode(), self.create(title="").data)


class PostReadTests(PostTestBase):
    def test_empty_list(self):
        response = self.client.get("/post")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Постів поки немає".encode(), response.data)

    def test_list_shows_posts_with_details(self):
        self.add_post(title="Flask ORM", category="tech", posted=datetime(2026, 11, 5, 14, 0))
        page = self.client.get("/post").data.decode()
        self.assertIn("Flask ORM", page)
        self.assertIn("05.11.2026", page)
        self.assertIn("img/default.jpg", page)
        self.assertIn("/post/1", page)
        self.assertIn("/post/create", page)
        self.assertIn("css/posts.css", page)

    def test_list_shows_only_active_posts(self):
        self.add_post(title="Visible post")
        self.add_post(title="Hidden post", is_active=False)
        page = self.client.get("/post").data.decode()
        self.assertIn("Visible post", page)
        self.assertNotIn("Hidden post", page)

    def test_list_sorted_by_date_descending(self):
        self.add_post(title="Old post", posted=datetime(2026, 1, 1))
        self.add_post(title="New post", posted=datetime(2026, 6, 1))
        self.add_post(title="Middle post", posted=datetime(2026, 3, 1))
        page = self.client.get("/post").data.decode()
        self.assertLess(page.index("New post"), page.index("Middle post"))
        self.assertLess(page.index("Middle post"), page.index("Old post"))

    def test_list_truncates_content_to_100_chars(self):
        self.add_post(content="a" * 100 + "TAIL")
        page = self.client.get("/post").data.decode()
        self.assertIn("a" * 100, page)
        self.assertNotIn("TAIL", page)

    def test_detail_shows_full_post(self):
        post_id = self.add_post(title="Detailed", content="b" * 100 + "TAIL", author="dmytro",
                                category="news", posted=datetime(2026, 11, 5, 14, 0))
        page = self.client.get(f"/post/{post_id}").data.decode()
        for text in ("Detailed", "TAIL", "dmytro", "Новина", "05.11.2026 14:00",
                     f"/post/{post_id}/update", f"/post/{post_id}/delete"):
            self.assertIn(text, page)

    def test_detail_not_found(self):
        response = self.client.get("/post/999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Пост з id 999 не знайдено".encode(), response.data)

    def test_html_in_post_is_escaped(self):
        post_id = self.add_post(title="<script>alert(1)</script>")
        for url in ("/post", f"/post/{post_id}"):
            data = self.client.get(url).data
            self.assertNotIn(b"<script>alert(1)</script>", data)
            self.assertIn(b"&lt;script&gt;", data)


class PostUpdateTests(PostTestBase):
    def test_update_form_is_prefilled(self):
        post_id = self.add_post(title="Docker", content="Containers", category="tech",
                                posted=datetime(2026, 11, 5, 14, 0))
        page = self.client.get(f"/post/{post_id}/update").data.decode()
        self.assertIn('value="Docker"', page)
        self.assertIn("Containers", page)
        self.assertIn('value="2026-11-05T14:00"', page)
        self.assertRegex(page, r'<option selected value="tech">')

    def test_update_post(self):
        post_id = self.add_post(title="Docker", author="admin")
        response = self.client.post(f"/post/{post_id}/update", data={
            "title": "Docker Update", "content": "New content", "is_active": "y",
            "publish_date": "2026-11-11T08:15", "category": "publication"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith(f"/post/{post_id}"))

        post = self.get_post(post_id)
        self.assertEqual((post.title, post.content, post.category),
                         ("Docker Update", "New content", "publication"))
        self.assertEqual(post.posted, datetime(2026, 11, 11, 8, 15))
        self.assertEqual(post.author, "admin")  # автор не змінюється
        self.assertEqual(len(self.all_posts()), 1)
        self.assertIn("Пост оновлено".encode(), self.client.get(f"/post/{post_id}").data)

    def test_update_can_hide_post(self):
        post_id = self.add_post()
        self.client.post(f"/post/{post_id}/update", data={
            "title": "Existing post", "content": "Some content",
            "publish_date": "2026-11-11T08:15", "category": "other"})
        self.assertFalse(self.get_post(post_id).is_active)

    def test_update_invalid_does_not_change_post(self):
        post_id = self.add_post(title="Docker")
        response = self.client.post(f"/post/{post_id}/update", data={
            "title": "", "content": "x", "category": "tech"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_post(post_id).title, "Docker")

    def test_update_not_found(self):
        self.assertEqual(self.client.get("/post/42/update").status_code, 404)
        self.assertEqual(self.client.post("/post/42/update", data=VALID).status_code, 404)


class PostDeleteTests(PostTestBase):
    def test_delete_confirmation_page(self):
        post_id = self.add_post(title="To be removed")
        response = self.client.get(f"/post/{post_id}/delete")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"To be removed", response.data)
        self.assertIn(b'method="post"', response.data.lower())
        self.assertIn(f'href="/post/{post_id}"'.encode(), response.data)  # кнопка «Скасувати»
        self.assertIsNotNone(self.get_post(post_id))  # GET нічого не видаляє

    def test_delete_post(self):
        post_id = self.add_post()
        other_id = self.add_post(title="Keep me")
        response = self.client.post(f"/post/{post_id}/delete")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/post"))
        self.assertIsNone(self.get_post(post_id))
        self.assertIsNotNone(self.get_post(other_id))
        self.assertIn("Пост успішно видалено".encode(), self.client.get("/post").data)
        self.assertEqual(self.client.get(f"/post/{post_id}").status_code, 404)

    def test_delete_not_found(self):
        self.assertEqual(self.client.get("/post/77/delete").status_code, 404)
        self.assertEqual(self.client.post("/post/77/delete").status_code, 404)


class PostCsrfTests(PostTestBase):
    csrf = True

    def test_forms_contain_csrf_token(self):
        post_id = self.add_post()
        for url in ("/post/create", f"/post/{post_id}/update", f"/post/{post_id}/delete"):
            self.assertIn(b'name="csrf_token"', self.client.get(url).data)

    def test_create_without_token_is_rejected(self):
        response = self.create()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.all_posts(), [])

    def test_delete_without_token_is_rejected(self):
        post_id = self.add_post()
        self.client.post(f"/post/{post_id}/delete")
        self.assertIsNotNone(self.get_post(post_id))


class ErrorPageTests(PostTestBase):
    def test_unknown_page_shows_custom_404(self):
        response = self.client.get("/no-such-page")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"404", response.data)
        self.assertIn("На головну".encode(), response.data)


if __name__ == "__main__":
    unittest.main()
