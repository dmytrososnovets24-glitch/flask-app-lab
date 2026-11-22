from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError

from app import db

from .models import User


def strip(value):
    return value.strip() if isinstance(value, str) else value


def strip_lower(value):
    return value.strip().lower() if isinstance(value, str) else value


class RegistrationForm(FlaskForm):
    username = StringField(
        "Ім'я користувача",
        filters=[strip],
        validators=[
            DataRequired(message="Вкажіть ім'я користувача."),  # обов'язкове поле
            Length(min=4, max=14, message="Ім'я має містити від 4 до 14 символів."),
            Regexp(r'^[A-Za-z][A-Za-z0-9_.]*$',
                   message="Ім'я має починатися з латинської літери й містити лише літери, "
                           "цифри, крапки або підкреслення."),
        ],
    )
    email = StringField(
        'Email',
        filters=[strip_lower],
        validators=[
            DataRequired(message='Вкажіть електронну пошту.'),
            Email(message='Введіть коректну адресу електронної пошти.'),
        ],
    )
    password = PasswordField(
        'Пароль',
        validators=[
            DataRequired(message='Вкажіть пароль.'),
            Length(min=6, message='Пароль має містити щонайменше 6 символів.'),
        ],
    )
    confirm_password = PasswordField(
        'Підтвердження пароля',
        validators=[
            DataRequired(message='Повторіть пароль.'),
            EqualTo('password', message='Паролі не збігаються.'),  # повторна перевірка пароля
        ],
    )
    submit = SubmitField('Зареєструватися')

    # перевірка унікальності username та email у БД
    def validate_username(self, field):
        if db.session.scalar(db.select(User).filter_by(username=field.data)):
            raise ValidationError(f"Користувач з ім'ям {field.data} уже існує.")

    def validate_email(self, field):
        if db.session.scalar(db.select(User).filter_by(email=field.data)):
            raise ValidationError(f'Користувач з email {field.data} уже існує.')

    def validate_password(self, field):
        if len(field.data.encode('utf-8')) > 72:
            raise ValidationError('Пароль задовгий: bcrypt враховує не більше 72 байтів.')


class LoginForm(FlaskForm):
    email = StringField(
        'Email',
        filters=[strip_lower],
        validators=[
            DataRequired(message='Вкажіть електронну пошту.'),
            Email(message='Введіть коректну адресу електронної пошти.'),
        ],
    )
    password = PasswordField('Пароль', validators=[DataRequired(message='Вкажіть пароль.')])
    remember = BooleanField("Запам'ятати мене")
    submit = SubmitField('Увійти')
