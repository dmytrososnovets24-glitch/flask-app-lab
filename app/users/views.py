import re
from urllib.parse import urlsplit

from flask import current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.orm import selectinload

from app import db

from . import users_bp
from .forms import LoginForm, RegistrationForm
from .models import User

PROTECTED_COOKIES = {'session', 'remember_token'}
COOKIE_KEY_RE = re.compile(r'^[A-Za-z0-9_-]{1,50}$')
THEMES = ('light', 'dark')


@users_bp.route('/hi/<string:name>')  # /users/hi/ivan?age=45
def greetings(name):
    name = name.upper()
    age = request.args.get('age', None, int)

    return render_template('users/hi.html', title='Привітання', name=name, age=age)


@users_bp.route('/admin')
def admin():
    to_url = url_for('users.greetings', name='administrator', age=45)
    return redirect(to_url)


def safe_next(target):
    """Повертає адресу з ?next= лише якщо вона веде на цей самий сайт."""
    if not target or not target.startswith('/') or target.startswith('//'):
        return None
    parts = urlsplit(target)
    return None if parts.scheme or parts.netloc else target


@users_bp.route('/register', methods=['GET', 'POST'])
def register():
    # авторизований користувач не реєструється вдруге
    if current_user.is_authenticated:
        return redirect(url_for('users.account'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # 1. дані з форми реєстрації; 2. хеш пароля (Flask-Bcrypt) і збереження в БД
        user = User(username=form.username.data, email=form.email.data, password=form.password.data)
        user.hash_password()
        db.session.add(user)
        db.session.commit()
        flash(f'Обліковий запис для {user.username} створено! Тепер можна увійти.', 'success')
        return redirect(url_for('users.login'))
    return render_template('users/register.html', form=form, title='Реєстрація')


@users_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('users.account'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).filter_by(email=form.email.data))
        # перевірка пароля через порівняння хешів
        if user and user.check_password(form.password.data):
            # login_user записує id користувача в сесію (рядком)
            login_user(user, remember=form.remember.data)
            flash(f'Вітаємо, {user.username}! Вхід виконано успішно.', 'success')
            return redirect(safe_next(request.args.get('next')) or url_for('users.account'))
        flash('Неправильний email або пароль.', 'danger')
    return render_template('users/login.html', form=form, title='Вхід')


@users_bp.route('/account')
@login_required
def account():
    # current_user — об'єкт автентифікованого користувача з полями моделі User
    return render_template('users/account.html', title='Профіль', user=current_user)


@users_bp.route('/', strict_slashes=False)
@login_required
def users_list():
    # пости користувачів завантажуються одним додатковим запитом (без N+1)
    users = db.session.scalars(db.select(User).options(selectinload(User.posts)).order_by(User.id)).all()
    return render_template('users/users.html', title='Користувачі', users=users)


@users_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()  # завершення сесії користувача
    flash('Ви вийшли з системи.', 'info')
    return redirect(url_for('users.login'))


@users_bp.route('/profile')
@login_required
def profile():
    theme = request.cookies.get(current_app.config['THEME_COOKIE'], 'light')
    if theme not in THEMES:
        theme = 'light'
    return render_template('users/profile.html', title='Кукі та тема', user=current_user.username,
                           cookies=request.cookies, theme=theme,
                           protected=PROTECTED_COOKIES)


@users_bp.route('/cookies/add', methods=['POST'])
@login_required
def add_cookie():
    key = request.form.get('key', '').strip()
    value = request.form.get('value', '')
    max_age = request.form.get('max_age', '', type=str).strip()

    if not COOKIE_KEY_RE.match(key):
        flash('Ключ кукі може містити лише літери, цифри, «-» та «_» (до 50 символів).', 'error')
        return redirect(url_for('users.profile'))
    if key in PROTECTED_COOKIES:
        flash(f'Кукі «{key}» службове, його змінювати не можна.', 'error')
        return redirect(url_for('users.profile'))
    if not max_age.isdigit() or int(max_age) <= 0:
        flash('Термін дії має бути додатним цілим числом секунд.', 'error')
        return redirect(url_for('users.profile'))

    response = make_response(redirect(url_for('users.profile')))
    response.set_cookie(key, value, max_age=int(max_age), samesite='Lax')
    flash(f'Кукі «{key}» додано на {int(max_age)} с.', 'success')
    return response


@users_bp.route('/cookies/delete', methods=['POST'])
@login_required
def delete_cookie():
    key = request.form.get('key', '').strip()

    if key in PROTECTED_COOKIES:
        flash(f'Кукі «{key}» службове, його видаляти не можна.', 'error')
        return redirect(url_for('users.profile'))
    if key not in request.cookies:
        flash(f'Кукі «{key}» не знайдено.', 'warning')
        return redirect(url_for('users.profile'))

    response = make_response(redirect(url_for('users.profile')))
    response.delete_cookie(key)
    flash(f'Кукі «{key}» видалено.', 'success')
    return response


@users_bp.route('/cookies/delete-all', methods=['POST'])
@login_required
def delete_all_cookies():
    response = make_response(redirect(url_for('users.profile')))
    removed = 0
    for key in request.cookies:
        if key not in PROTECTED_COOKIES:
            response.delete_cookie(key)
            removed += 1
    flash(f'Видалено кукі: {removed}. Службове кукі сесії збережено.', 'success')
    return response


@users_bp.route('/theme/<string:scheme>')
def set_theme(scheme):
    if scheme not in THEMES:
        flash('Невідома кольорова схема.', 'error')
        return redirect(url_for('users.profile'))

    response = make_response(redirect(url_for('users.profile')))
    response.set_cookie(current_app.config['THEME_COOKIE'], scheme,
                        max_age=current_app.config['THEME_MAX_AGE'], samesite='Lax')
    flash('Кольорову схему змінено на ' + ('темну.' if scheme == 'dark' else 'світлу.'), 'info')
    return response
