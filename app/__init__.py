from flask import Flask

app = Flask(__name__)
app.config.from_object('config.Config')

from . import views
from .users import users_bp
from .products import products_bp

app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(products_bp, url_prefix='/product')
