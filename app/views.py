from flask import current_app, flash, redirect, render_template, url_for

from . import app
from .contact_log import log_contact_message
from .forms import ContactForm

PROFILE = {
    'name': 'Сосновець Дмитро Сергійович',
    'position': 'Студент, початківець Python/Flask розробник',
    'email': 'dimasosnovec@gmail.com',
    'github': 'https://github.com/dmytrososnovets24-glitch',
}


@app.context_processor
def inject_profile():
    return {'profile': PROFILE}


@app.route('/')
def home():
    return render_template('homepage.html', title='Головна')


@app.route('/resume')
def resume():
    return render_template('resume.html', title='Резюме')


@app.route('/contacts', methods=['GET', 'POST'])
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
        return redirect(url_for('contacts'))

    if form.is_submitted():
        flash('Форму не надіслано: виправте помилки у виділених полях.', 'error')

    return render_template('contacts.html', title='Контакти', form=form)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', title='Сторінку не знайдено'), 404


@app.errorhandler(413)
def payload_too_large(error):
    flash('Файл завеликий. Максимальний розмір запиту — 5 МБ.', 'error')
    return render_template('404.html', title='Файл завеликий',
                           message='Завантажений файл перевищує допустимий розмір.'), 413
