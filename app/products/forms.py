import os
from decimal import Decimal

from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.fields.choices import SelectChoice
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, ValidationError

CATEGORIES = ['Електроніка', 'Побутова техніка', 'Одяг', 'Книги', 'Спорт', 'Інше']
ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg']

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
JPEG_SIGNATURE = b'\xff\xd8\xff'


def max_two_decimals(form, field):
    value = field.data
    if value is None:
        return
    if not value.is_finite():
        raise ValidationError('Введіть коректне число.')
    if -value.as_tuple().exponent > 2:
        raise ValidationError('Ціна може мати не більше двох знаків після коми.')


class ProductForm(FlaskForm):
    name = StringField(
        'Назва',
        validators=[
            DataRequired(message='Вкажіть назву товару.'),
            Length(min=3, max=100, message='Назва має містити від 3 до 100 символів.'),
        ],
    )
    content = TextAreaField(
        'Опис',
        validators=[
            DataRequired(message='Додайте опис товару.'),
            Length(max=2000, message='Опис має містити не більше 2000 символів.'),
        ],
        render_kw={'rows': 5, 'cols': 40},
    )
    price = DecimalField(
        'Ціна, $',
        places=2,
        validators=[
            InputRequired(message='Вкажіть ціну.'),
            NumberRange(min=Decimal('0.01'), message='Ціна має бути більшою за нуль.'),
            max_two_decimals,
        ],
        render_kw={'step': '0.01', 'min': '0.01'},
    )
    category = SelectField(
        'Категорія',
        choices=[SelectChoice(c, c) for c in CATEGORIES],
        validators=[DataRequired(message='Оберіть категорію.')],
    )
    quantity = IntegerField(
        'Кількість, шт.',
        validators=[
            InputRequired(message='Вкажіть кількість.'),
            NumberRange(min=0, message='Кількість не може бути від’ємною.'),
        ],
        render_kw={'min': '0'},
    )
    image = FileField(
        'Зображення (PNG, JPG, JPEG)',
        validators=[FileAllowed(ALLOWED_EXTENSIONS, 'Дозволені лише зображення PNG, JPG та JPEG.')],
    )
    submit = SubmitField('Зберегти')

    def validate_image(self, field):
        """Перевіряє розмір файлу та відповідність вмісту розширенню."""
        file = field.data
        if not file or not getattr(file, 'filename', ''):
            return
        if field.errors:  # розширення вже відхилено
            return

        stream = file.stream
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)
        limit = current_app.config['MAX_IMAGE_SIZE']
        if size > limit:
            raise ValidationError(f'Файл завеликий: максимум {limit // (1024 * 1024)} МБ.')

        header = stream.read(8)
        stream.seek(0)
        ext = file.filename.rsplit('.', 1)[-1].lower()
        is_png = header.startswith(PNG_SIGNATURE)
        is_jpeg = header.startswith(JPEG_SIGNATURE)
        if (ext == 'png' and not is_png) or (ext in ('jpg', 'jpeg') and not is_jpeg):
            raise ValidationError('Вміст файлу не відповідає його розширенню.')


class DeleteForm(FlaskForm):
    """Порожня форма: потрібна для CSRF-захисту POST-запиту на видалення."""
    submit = SubmitField('Видалити')
