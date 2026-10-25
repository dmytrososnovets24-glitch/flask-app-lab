import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    TESTING = False

    # Заглушка для автентифікації (без бази даних)
    AUTH_USERNAME = 'admin'
    AUTH_PASSWORD = '12345'

    THEME_COOKIE = 'theme'
    THEME_MAX_AGE = 60 * 60 * 24 * 30  # 30 днів
