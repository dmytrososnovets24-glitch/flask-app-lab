from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import (BooleanField, DateTimeLocalField, SelectField, SelectMultipleField,
                     StringField, SubmitField, TextAreaField)
from wtforms.fields.choices import SelectChoice
from wtforms.validators import DataRequired, InputRequired, Length, Optional, ValidationError

from app import db
from app.users.models import User

from .models import CATEGORIES, Tag

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
    # автор поста — один із користувачів з БД
    author_id = SelectField(
        'Автор',
        coerce=int,
        validate_choice=False,  # перевірку виконує validate_author_id з українським повідомленням
        validators=[InputRequired(message='Оберіть автора.')],
    )
    # декілька тегів поста (зв'язок багато до багатьох)
    tags = SelectMultipleField(
        'Теги',
        coerce=int,
        validate_choice=False,  # перевірку виконує validate_tags
        validators=[Optional()],
        render_kw={'size': 5},
    )
    submit = SubmitField('Додати пост')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # список авторів із БД (синтаксис SQLAlchemy 2.0)
        authors = db.session.scalars(db.select(User).order_by(User.id)).all()
        self.author_id.choices = [SelectChoice(a.id, a.username) for a in authors]
        tags = db.session.scalars(db.select(Tag).order_by(Tag.name)).all()
        self.tags.choices = [SelectChoice(t.id, t.name) for t in tags]

    def validate_author_id(self, field):
        if field.data is None or db.session.get(User, field.data) is None:
            raise ValidationError('Оберіть автора зі списку.')

    def validate_tags(self, field):
        known = {choice.value for choice in field.choices}
        if any(tag_id not in known for tag_id in field.data or []):
            raise ValidationError('Оберіть теги зі списку.')


class DeletePostForm(FlaskForm):
    """Порожня форма: потрібна для CSRF-захисту POST-запиту на видалення."""
    submit = SubmitField('Так, видалити')
