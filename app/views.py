from flask import render_template, request

from . import app

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
    sent = request.method == 'POST'
    sender = request.form.get('name', '') if sent else ''
    return render_template('contacts.html', title='Контакти', sent=sent, sender=sender)
