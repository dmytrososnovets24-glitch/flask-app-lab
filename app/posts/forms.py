from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import (BooleanField, DateTimeLocalField, SelectField, StringField,
                     SubmitField, TextAreaField)
from wtforms.fields.choices import SelectChoice
from wtforms.validators import DataRequired, Length, Optional

from .models import CATEGORIES

CATEGORY_LABELS = {
    'news': 'Новина',
    'publication': 'Публікація',
    'tech': 'Технології',
    'other': 'Інше',
}


class PostForm(FlaskForm):
    title = StringField(
        'Заголовок',
        validators=[
            DataRequired(message='Вкажіть заголовок.'),
            Length(min=2, max=150, message='Заголовок має містити від 2 до 150 символів.'),
        ],
    )
    content = TextAreaField(
        'Текст',
        render_kw={'rows': 5, 'cols': 40},
        validators=[DataRequired(message='Додайте текст поста.')],
    )
    is_active = BooleanField('Активний пост', default=True)
    # поле для вибору дати й часу публікації
    publish_date = DateTimeLocalField(
        'Дата публікації',
        format=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S'],
        default=datetime.now,
        validators=[Optional()],
    )
    category = SelectField(
        'Категорія',
        choices=[SelectChoice(value, CATEGORY_LABELS[value]) for value in CATEGORIES],
        validators=[DataRequired(message='Оберіть категорію.')],
    )
    submit = SubmitField('Додати пост')


class DeletePostForm(FlaskForm):
    """Порожня форма: потрібна для CSRF-захисту POST-запиту на видалення."""
    submit = SubmitField('Так, видалити')
