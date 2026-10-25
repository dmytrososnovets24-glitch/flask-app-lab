from flask import redirect, render_template, request, url_for

from . import users_bp


@users_bp.route('/hi/<string:name>')  # /users/hi/ivan?age=45
def greetings(name):
    name = name.upper()
    age = request.args.get('age', None, int)

    return render_template('users/hi.html', title='Привітання', name=name, age=age)


@users_bp.route('/admin')
def admin():
    to_url = url_for('users.greetings', name='administrator', age=45)
    return redirect(to_url)
