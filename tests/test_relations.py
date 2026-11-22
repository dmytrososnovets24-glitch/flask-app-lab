import unittest
from datetime import datetime

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app import create_app, db
from app.posts.models import Post, Tag, post_tags
from app.users.models import User


class RelationTestBase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def user(self, username):
        user = User(username=username, email=f"{username}@example.com", password="pass")
        db.session.add(user)
        return user

    def post(self, title, user=None, tags=()):
        post = Post(title=title, content=f"Text of {title}", user=user, tags=list(tags))
        db.session.add(post)
        return post


class UserPostRelationTests(RelationTestBase):
    """Зв'язок «один до багатьох»: User.posts <-> Post.user."""

    def test_posts_of_user(self):
        dmytro, andrii = self.user("dmytro"), self.user("andrii")
        self.post("First", andrii)
        self.post("Second", andrii)
        self.post("Third", dmytro)
        db.session.commit()
        # колекції зв'язків завантажуються без ORDER BY, тому порівнюємо без урахування порядку
        self.assertEqual(sorted(p.title for p in db.session.get(User, andrii.id).posts), ["First", "Second"])
        self.assertEqual([p.title for p in db.session.get(User, dmytro.id).posts], ["Third"])

    def test_back_populates_both_sides(self):
        dmytro = self.user("dmytro")
        post = Post(title="Hello", content="text")
        dmytro.posts.append(post)  # зміна з боку User ...
        self.assertIs(post.user, dmytro)  # ... одразу видна з боку Post
        db.session.commit()
        self.assertEqual(post.user_id, dmytro.id)

    def test_post_without_user(self):
        post = self.post("Orphan")
        db.session.commit()
        self.assertIsNone(post.user_id)
        self.assertIsNone(post.user)

    def test_deleting_user_deletes_posts(self):
        dmytro, andrii = self.user("dmytro"), self.user("andrii")
        self.post("Mine", dmytro)
        self.post("Not mine", andrii)
        db.session.commit()
        db.session.delete(dmytro)  # cascade="all, delete-orphan"
        db.session.commit()
        self.assertEqual([p.title for p in db.session.scalars(db.select(Post))], ["Not mine"])

    def test_username_and_email_are_unique(self):
        self.user("dmytro")
        db.session.commit()
        db.session.add(User(username="dmytro", email="other@example.com", password="x"))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        db.session.add(User(username="other", email="dmytro@example.com", password="x"))
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_user_repr(self):
        self.assertEqual(repr(User(username="dmytro", email="d@example.com")),
                         "User('dmytro', 'd@example.com')")


class TagRelationTests(RelationTestBase):
    """Зв'язок «багато до багатьох»: Post.tags <-> Tag.posts через post_tags."""

    def test_tags_of_post_and_posts_of_tag(self):
        python, flask, web = Tag(name="Python"), Tag(name="Flask"), Tag(name="Web")
        first = self.post("First")
        second = self.post("Second")
        first.tags.append(python)
        first.tags.append(flask)
        second.tags.append(flask)
        db.session.add(web)
        db.session.commit()
        self.assertEqual(sorted(t.name for t in first.tags), ["Flask", "Python"])
        self.assertEqual(sorted(p.title for p in flask.posts), ["First", "Second"])
        self.assertEqual(web.posts, [])

    def test_association_rows(self):
        flask = Tag(name="Flask")
        post = self.post("First", tags=[flask])
        db.session.commit()
        rows = db.session.execute(db.select(post_tags)).all()
        self.assertEqual([(r.post_id, r.tag_id) for r in rows], [(post.id, flask.id)])

    def test_deleting_post_removes_only_links(self):
        flask = Tag(name="Flask")
        post = self.post("First", tags=[flask])
        db.session.commit()
        db.session.delete(post)
        db.session.commit()
        self.assertEqual(db.session.execute(db.select(post_tags)).all(), [])
        self.assertIsNotNone(db.session.get(Tag, flask.id))  # сам тег лишається

    def test_tag_name_is_unique(self):
        db.session.add(Tag(name="Flask"))
        db.session.commit()
        db.session.add(Tag(name="Flask"))
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_tag_repr(self):
        self.assertEqual(repr(Tag(name="Flask")), "<Tag Flask>")


class LoadingStrategyTests(RelationTestBase):
    """Пункт 13: кількість SELECT без .options() і з joinedload()/selectinload()."""

    def setUp(self):
        super().setUp()
        dmytro, andrii = self.user("dmytro"), self.user("andrii")
        python, flask, orm = Tag(name="Python"), Tag(name="Flask"), Tag(name="SQLAlchemy")
        self.post("P1", dmytro, [python, flask, orm])  # допис із кількома тегами
        self.post("P2", andrii, [flask])                # тег Flask — у кількох дописах
        self.post("P3", dmytro, [flask, orm])
        self.post("P4", andrii, [python])
        self.post("P5", dmytro)
        db.session.commit()
        db.session.expunge_all()  # нова «чиста» ORM-сесія для вимірювання

        self.selects = []

        def count_select(conn, cursor, statement, *args):
            if statement.lstrip().upper().startswith("SELECT"):
                self.selects.append(statement)

        event.listen(db.engine, "before_cursor_execute", count_select)
        self.addCleanup(event.remove, db.engine, "before_cursor_execute", count_select)

    def run_loop(self, stmt):
        posts = db.session.scalars(stmt).all()
        return [(p.title, p.user.username, sorted(t.name for t in p.tags)) for p in posts]

    def test_without_options_runs_n_plus_one_queries(self):
        rows = self.run_loop(db.select(Post).order_by(Post.id.desc()))
        self.assertEqual(len(rows), 5)
        # 1 запит на дописи + 2 на авторів (далі з identity map) + 5 на теги кожного допису
        self.assertEqual(len(self.selects), 1 + 2 + 5)

    def test_with_joinedload_and_selectinload_runs_two_queries(self):
        stmt = (
            db.select(Post)
            .options(joinedload(Post.user), selectinload(Post.tags))
            .order_by(Post.id.desc())
        )
        rows = self.run_loop(stmt)
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(self.selects), 2)
        self.assertIn("JOIN users", self.selects[0])
        self.assertIn("post_tags", self.selects[1])

    def test_both_variants_return_same_data(self):
        plain = self.run_loop(db.select(Post).order_by(Post.id.desc()))
        db.session.expunge_all()
        optimized = self.run_loop(
            db.select(Post).options(joinedload(Post.user), selectinload(Post.tags))
            .order_by(Post.id.desc()))
        self.assertEqual(plain, optimized)
        self.assertEqual(plain[-1], ("P1", "dmytro", ["Flask", "Python", "SQLAlchemy"]))

    def test_posts_page_uses_constant_number_of_queries(self):
        db.session.remove()
        self.selects.clear()
        response = self.app.test_client().get("/post")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.selects), 2)


class SqlEchoConfigTests(unittest.TestCase):
    def test_echo_is_off_by_default(self):
        app = create_app("testing")
        self.assertFalse(app.config["SQLALCHEMY_ECHO"])


if __name__ == "__main__":
    unittest.main()
