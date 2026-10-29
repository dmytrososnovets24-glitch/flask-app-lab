"""Зберігання товарів у JSON-файлі за допомогою TinyDB."""
import os
import uuid
from contextlib import contextmanager
from datetime import datetime

from flask import current_app
from tinydb import TinyDB
from tinydb.table import Document

from . import products_bp

TABLE_NAME = 'products'

SEED_PRODUCTS = [
    {
        'name': 'Laptop',
        'content': 'Потужний ноутбук з процесором Intel Core i7, 16 ГБ оперативної пам’яті та SSD на 512 ГБ.',
        'price': 1200.00, 'category': 'Електроніка', 'quantity': 10,
    },
    {
        'name': 'Phone',
        'content': 'Смартфон із 6.5-дюймовим OLED-дисплеєм, подвійною камерою та акумулятором на 5000 мА·год.',
        'price': 800.00, 'category': 'Електроніка', 'quantity': 25,
    },
    {
        'name': 'PC',
        'content': 'Настільний комп’ютер для ігор або роботи з графікою: RTX 4070, 32 ГБ RAM, 1 ТБ SSD.',
        'price': 1800.00, 'category': 'Електроніка', 'quantity': 5,
    },
]


def now_iso():
    return datetime.now().isoformat(timespec='seconds')


@contextmanager
def products_table():
    """Відкриває сховище, створює файл і таблицю за потреби, закриває після використання."""
    path = current_app.config['PRODUCTS_DB_PATH']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fresh = not os.path.exists(path)
    db = TinyDB(path, indent=2, ensure_ascii=False, encoding='utf-8')
    try:
        table = db.table(TABLE_NAME)
        if fresh and current_app.config.get('SEED_PRODUCTS'):
            for item in SEED_PRODUCTS:
                _insert(table, {**item, 'image': None, 'created_at': now_iso()})
        yield table
    finally:
        db.close()


def _next_id(table):
    return max((doc.doc_id for doc in table.all()), default=0) + 1


def _insert(table, data):
    product_id = _next_id(table)
    table.insert(Document({**data, 'id': product_id}, doc_id=product_id))
    return product_id


def _as_dict(doc):
    return {**doc, 'id': doc.doc_id}


def all_products():
    with products_table() as table:
        return sorted((_as_dict(doc) for doc in table.all()), key=lambda p: p['id'])


def get_product(product_id):
    with products_table() as table:
        doc = table.get(doc_id=product_id)
        return _as_dict(doc) if doc is not None else None


def add_product(data):
    """Додає товар; id і created_at встановлюються автоматично."""
    with products_table() as table:
        return _insert(table, {**data, 'created_at': now_iso()})


def update_product(product_id, data):
    """Оновлює поля товару, не змінюючи id та created_at."""
    data = {k: v for k, v in data.items() if k not in ('id', 'created_at')}
    with products_table() as table:
        if not table.contains(doc_id=product_id):
            return False
        table.update(data, doc_ids=[product_id])
        return True


def delete_product(product_id):
    """Видаляє товар; повертає видалений запис або None."""
    with products_table() as table:
        doc = table.get(doc_id=product_id)
        if doc is None:
            return None
        table.remove(doc_ids=[product_id])
        return _as_dict(doc)


# --- зображення ---------------------------------------------------------------

def upload_dir():
    configured = current_app.config.get('PRODUCTS_UPLOAD_DIR')
    return configured or os.path.join(products_bp.static_folder, 'uploads')


def save_image(file_storage):
    """Зберігає завантажений файл під випадковим UUID-ім'ям; повертає відносний шлях."""
    ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    directory = upload_dir()
    os.makedirs(directory, exist_ok=True)
    file_storage.save(os.path.join(directory, filename))
    return f'uploads/{filename}'


def image_file_path(relative_path):
    """Безпечний повний шлях до файлу зображення за збереженим відносним шляхом."""
    if not relative_path:
        return None
    return os.path.join(upload_dir(), os.path.basename(relative_path))


def delete_image(relative_path):
    path = image_file_path(relative_path)
    if path and os.path.isfile(path):
        os.remove(path)
