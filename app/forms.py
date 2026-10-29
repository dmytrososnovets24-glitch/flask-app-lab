from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.fields.choices import SelectChoice
from wtforms.validators import DataRequired, Email, Length, Regexp

SUBJECT_LABELS = {
    'question': 'Запитання',
    'cooperation': 'Співпраця',
    'feedback': 'Відгук про сайт',
    'other': 'Інше',
}
SUBJECT_CHOICES = [SelectChoice('', '— оберіть тему —')] + [
    SelectChoice(value, label) for value, label in SUBJECT_LABELS.items()
]


class ContactForm(FlaskForm):
    name = StringField(
        "Ім'я",
        validators=[
            DataRequired(message="Вкажіть ім'я."),
            Length(min=4, max=10, message="Ім'я має містити від 4 до 10 символів."),
        ],
    )
    email = StringField(
        'E-mail',
        validators=[
            DataRequired(message='Вкажіть електронну пошту.'),
            Email(message='Введіть коректну адресу електронної пошти.'),
        ],
    )
    phone = StringField(
        'Телефон',
        validators=[
            DataRequired(message='Вкажіть номер телефону.'),
            Regexp(r'^\+380\d{9}$', message='Формат телефону: +380XXXXXXXXX (9 цифр після +380).'),
        ],
        render_kw={'placeholder': '+380501234567'},
    )
    subject = SelectField(
        'Тема',
        choices=SUBJECT_CHOICES,
        validators=[DataRequired(message='Оберіть тему повідомлення.')],
    )
    message = TextAreaField(
        'Повідомлення',
        validators=[
            DataRequired(message='Напишіть повідомлення.'),
            Length(max=500, message='Повідомлення має містити не більше 500 символів.'),
        ],
        render_kw={'rows': 5},
    )
    submit = SubmitField('Надіслати')

    def subject_label(self):
        """Людська назва вибраної теми для логу."""
        return SUBJECT_LABELS.get(self.subject.data, self.subject.data)
