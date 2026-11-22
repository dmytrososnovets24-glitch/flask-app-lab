from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from .contact_log import log_contact_message
from .forms import ContactForm

main_bp = Blueprint('main', __name__)

PROFILE = {
    'name': 'Сосновець Дмитро Сергійович',
    'position': 'Студент, початківець Python/Flask розробник',
    'email': 'dimasosnovec@gmail.com',
    'github': 'https://github.com/dmytrososnovets24-glitch',
}


@main_bp.app_context_processor
def inject_profile():
    return {'profile': PROFILE}


@main_bp.route('/')
def home():
    return render_template('homepage.html', title='Головна')


@main_bp.route('/resume')
def resume():
    return render_template('resume.html', title='Резюме')


@main_bp.route('/contacts', methods=['GET', 'POST'])
def contacts():
    form = ContactForm()

    if form.validate_on_submit():
        try:
            log_contact_message(current_app.config['CONTACT_LOG_FILE'], form)
        except OSError:
            current_app.logger.exception('Не вдалося записати повідомлення контактної форми')
            flash('Не вдалося зберегти повідомлення. Спробуйте пізніше.', 'error')
        else:
            flash(f'Дякуємо, {form.name.data}! Повідомлення надіслано та збережено.', 'success')
        # Post/Redirect/Get: після обробки форми робимо перенаправлення
        return redirect(url_for('main.contacts'))

    if form.is_submitted():
        flash('Форму не надіслано: виправте помилки у виділених полях.', 'error')

    return render_template('contacts.html', title='Контакти', form=form)
