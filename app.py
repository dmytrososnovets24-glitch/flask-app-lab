from flask import Flask, render_template, request

app = Flask(__name__)

PROFILE = {
    'name': 'Сосновець Дмитро Сергійович',
    'position': 'Студент, початківець Python/Flask розробник',
    'email': 'dimasosnovec@gmail.com',
    'github': 'https://github.com/dmytrososnovets24-glitch',
}


@app.route('/')
@app.route('/resume')
def resume():
    return render_template('resume.html', title='Резюме', profile=PROFILE)


@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    sent = request.method == 'POST'
    sender = request.form.get('name', '') if sent else ''
    return render_template('contacts.html', title='Контакти', profile=PROFILE,
                           sent=sent, sender=sender)


if __name__ == '__main__':
    app.run(debug=True)
