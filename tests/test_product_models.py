import os
import unittest
import warnings
from unittest import mock

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.products.models import Category, Product

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations")


class ModelTestBase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        # створення таблиць у тестовій базі (SQLite в пам'яті)
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def save(self, *objects):
        db.session.add_all(objects)
        db.session.commit()


class ProductModelTests(ModelTestBase):
    def test_create_product(self):
        self.save(Product(name="Pc", price=700))
        product = db.session.get(Product, 1)
        self.assertEqual(product.name, "Pc")
        self.assertEqual(product.price, 700.0)

    def test_active_is_true_by_default(self):
        product = Product(name="MAC", price=500)
        self.save(product)
        self.assertIs(product.active, True)

    def test_active_can_be_false(self):
        product = Product(name="Gaming Laptop", price=1500.00, active=False)
        self.save(product)
        self.assertIs(db.session.get(Product, product.id).active, False)

    def test_created_at_is_set_by_database(self):
        product = Product(name="iPhone 15", price=999.99)
        self.save(product)
        self.assertIsNotNone(product.created_at)

    def test_name_is_required(self):
        db.session.add(Product(price=10))
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_price_is_required(self):
        db.session.add(Product(name="No price"))
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_category_is_optional(self):
        product = Product(name="iPhone 15", price=999.99)
        self.save(product)
        self.assertIsNone(product.category_id)
        self.assertIsNone(product.category)

    def test_repr(self):
        self.assertEqual(repr(Product(name="Pc", price=700.0)), "<Product Pc - $700.0>")


class CategoryRelationTests(ModelTestBase):
    def test_product_belongs_to_category(self):
        laptops = Category(name="Laptops")
        product = Product(name="Gaming Laptop", price=1500.00, category=laptops)
        self.save(laptops, product)
        self.assertEqual(product.category.name, "Laptops")
        self.assertEqual(product.category_id, laptops.id)

    def test_category_has_many_products(self):
        laptops = Category(name="Laptops")
        self.save(
            laptops,
            Product(name="Gaming Laptop", price=1500.00, category=laptops),
            Product(name="Ultrabook", price=1100.00, category=laptops),
            Product(name="Novel", price=20.0),
        )
        self.assertEqual([p.name for p in laptops.products], ["Gaming Laptop", "Ultrabook"])

    def test_append_product_through_category(self):
        books = Category(name="Books")
        books.products.append(Product(name="Novel", price=20.0))
        self.save(books)
        novel = db.session.execute(db.select(Product)).scalar_one()
        self.assertEqual(novel.category, books)

    def test_category_name_is_unique(self):
        self.save(Category(name="Books"))
        db.session.add(Category(name="Books"))
        with self.assertRaises(IntegrityError):
            db.session.commit()

    def test_category_repr(self):
        self.assertEqual(repr(Category(name="Books")), "<Category Books>")


class NamingConventionTests(ModelTestBase):
    def test_constraint_names_follow_convention(self):
        inspector = inspect(db.engine)
        self.assertEqual(inspector.get_pk_constraint("categories")["name"], "pk_categories")
        self.assertEqual(inspector.get_pk_constraint("products")["name"], "pk_products")
        self.assertEqual(
            inspector.get_unique_constraints("categories")[0]["name"], "uq_categories_name")
        self.assertEqual(
            inspector.get_foreign_keys("products")[0]["name"],
            "fk_products_category_id_categories")


class MigrationChainTests(unittest.TestCase):
    """Усі міграції застосовуються до порожньої бази і відкочуються назад."""

    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        # env.py не повинен переналаштовувати логування під час тестів
        patcher = mock.patch("logging.config.fileConfig")
        patcher.start()
        self.addCleanup(patcher.stop)
        # стандартний env.py Flask-Migrate спершу пробує застарілий get_engine()
        filters = warnings.catch_warnings()
        filters.__enter__()
        self.addCleanup(filters.__exit__, None, None, None)
        warnings.filterwarnings(
            "ignore", message="'get_engine' is deprecated", category=DeprecationWarning)

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def scalar(self, sql):
        return db.session.execute(db.text(sql)).scalar()

    def test_upgrade_builds_schema(self):
        upgrade(directory=MIGRATIONS_DIR)
        inspector = inspect(db.engine)
        self.assertTrue({"posts", "products", "categories"} <= set(inspector.get_table_names()))
        self.assertEqual(
            [c["name"] for c in inspector.get_columns("products")],
            ["id", "name", "price", "category_id", "active", "created_at"])
        self.assertEqual(
            inspector.get_foreign_keys("products")[0]["name"],
            "fk_products_category_id_categories")

    def test_upgrade_inserts_data(self):
        upgrade(directory=MIGRATIONS_DIR)
        self.assertEqual(self.scalar("SELECT count(*) FROM categories"), 3)
        self.assertEqual(self.scalar("SELECT count(*) FROM products"), 4)
        self.assertEqual(self.scalar("SELECT count(*) FROM products WHERE created_at IS NULL"), 0)
        tshirt = db.session.execute(db.select(Product).filter_by(name="T-Shirt")).scalar_one()
        self.assertIs(tshirt.active, False)
        self.assertEqual(tshirt.category.name, "Clothing")

    def test_models_match_migrated_schema(self):
        upgrade(directory=MIGRATIONS_DIR)
        with db.engine.connect() as connection:
            context = MigrationContext.configure(connection)
            self.assertEqual(compare_metadata(context, db.metadata), [])

    def test_downgrade_removes_inserted_data(self):
        upgrade(directory=MIGRATIONS_DIR)
        downgrade(directory=MIGRATIONS_DIR, revision="e1c97fc9abc8")  # ревізія перед вставкою даних
        self.assertEqual(self.scalar("SELECT count(*) FROM products"), 0)
        self.assertEqual(self.scalar("SELECT count(*) FROM categories"), 0)

    def test_downgrade_to_base(self):
        upgrade(directory=MIGRATIONS_DIR)
        downgrade(directory=MIGRATIONS_DIR, revision="base")
        self.assertEqual(inspect(db.engine).get_table_names(), ["alembic_version"])


if __name__ == "__main__":
    unittest.main()
