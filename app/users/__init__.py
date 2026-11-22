from flask import Blueprint

users_bp = Blueprint('users', __name__, template_folder='templates')

from . import models, views  # models — щоб Alembic бачив таблицю users
