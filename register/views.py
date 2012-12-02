from flask import Blueprint, request, render_template, url_for, session, flash
from register.forms import RegistrationForm
from register.models import User
from register.signals import user_registered
from auth.auth_settings import TOKENS_KEY

app = Blueprint('register', __name__)

@app.route('/', methods = ['GET', 'POST'])
def register():
    form = RegistrationForm(request.form, csrf_context=session)
    
    if request.method == "POST" and form.validate():
        users = User.get_collection()
        if not users.find_one({"email":form.email.data}):
            users.insert(User(email = form.email.data,
                              access_tokens = session[TOKENS_KEY]))
            user_registered.send(user)
            
        return redirect(url_for('.confirmation_sent'))
    else:
        selected = session[TOKENS_KEY].keys()
        
        return render_template('%s/index.html' % app.name,
            form = form, register_url = url_for(".register"),
            selected = selected)

@app.route('/confirmation_sent')
def confirmation_sent():
    return render_template('%s/confirmation_sent.html' % app.name)

@app.route('/confirm/<user_id>')
def confirm(user_id):
    """
    Activate user function.
    """
    found_user = User.get_collection().find_one({'_id': user_id})
    if not found_user:
        return abort(404)
    else:
        if not found_user['confirmed']:
            found_user['confirmed'] = True
            mailing.send_subscription_confirmed_mail(found_user)
            flash('user has been activated', 'info')
        elif found_user['confirmed']:
            flash('user already activated', 'info')
        return redirect(url_for('login'))
