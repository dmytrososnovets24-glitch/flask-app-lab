import os

from dotenv import load_dotenv

# корінь проєкту (тека, де лежать run.py, .env, instance/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    """Спільні налаштування для всіх режимів."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    DEBUG = False
    TESTING = False

    # база даних (відносний шлях SQLite розміщується в теці instance/)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///data.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # заглушка для автентифікації (без бази даних)
    AUTH_USERNAME = 'admin'
    AUTH_PASSWORD = '12345'

    THEME_COOKIE = 'theme'
    THEME_MAX_AGE = 60 * 60 * 24 * 30  # 30 днів

    CONTACT_LOG_FILE = os.path.join(BASE_DIR, 'logs', 'contact_messages.log')
    PRODUCTS_DB_PATH = os.path.join(BASE_DIR, 'data', 'products.json')
    PRODUCTS_UPLOAD_DIR = None  # None -> app/products/static/uploads
    SEED_PRODUCTS = True
    MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 МБ на одне зображення
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # жорсткий ліміт на весь запит


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # окрема база в пам'яті для тестів
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
