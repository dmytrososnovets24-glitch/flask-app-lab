import os

from flask import Flask, flash, render_template
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.exceptions import NotFound

from .config import config


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate()


def create_app(config_name=None):
    """Application factory: створює застосунок для вказаного режиму."""
    config_name = config_name or os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    from .views import main_bp
    from .users import users_bp
    from .products import products_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(products_bp, url_prefix='/product')

    @app.errorhandler(404)
    def not_found(error):
        # власний опис (abort(404, description=...)) показуємо, стандартний англійський — ні
        message = None if error.description == NotFound.description else error.description
        return render_template('404.html', title='Сторінку не знайдено', message=message), 404

    @app.errorhandler(413)
    def payload_too_large(error):
        flash('Файл завеликий. Максимальний розмір запиту — 5 МБ.', 'error')
        return render_template('404.html', title='Файл завеликий', code=413,
                               message='Завантажений файл перевищує допустимий розмір.'), 413

    return app
