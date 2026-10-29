import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    TESTING = False

    # Заглушка для автентифікації (без бази даних)
    AUTH_USERNAME = 'admin'
    AUTH_PASSWORD = '12345'

    THEME_COOKIE = 'theme'
    THEME_MAX_AGE = 60 * 60 * 24 * 30  # 30 днів

    # Лабораторна 5
    CONTACT_LOG_FILE = os.path.join(BASE_DIR, 'logs', 'contact_messages.log')
    PRODUCTS_DB_PATH = os.path.join(BASE_DIR, 'data', 'products.json')
    PRODUCTS_UPLOAD_DIR = None  # None -> app/products/static/uploads
    SEED_PRODUCTS = True
    MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 МБ на одне зображення
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # жорсткий ліміт на весь запит
