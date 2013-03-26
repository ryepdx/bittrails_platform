# -*- coding: utf-8 -*-
import app as core
from flask import (
    Blueprint, request, current_app, g, render_template, 
    redirect, flash, session, abort, url_for)
from provider import BitTrailsProvider
from models import AccessToken, User
from auth.signals import services_registered
from flask.ext.openid import OpenID

app = Blueprint('oauth_provider', __name__, template_folder='templates')

PROVIDER = BitTrailsProvider(current_app)
PROVIDER.init_blueprint(app)
oid = OpenID(current_app)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/callback')
def callback():
    return str(request.__dict__)


@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    """Does the login via OpenID.  Has to call into `oid.try_login`
    to start the OpenID machinery.
    """
    # if we are already logged in, go back to were we came from
    if g.user is not None:
        return redirect(oid.get_next_url())
    if request.method == 'POST':
        openid = request.form.get('openid')
        if openid:
            return oid.try_login(openid, ask_for=['email', 'fullname',
                                                  'nickname'])
    return render_template('login.html', next=oid.get_next_url(),
                           error=oid.fetch_error())


@app.route('/setup-account', methods=['GET', 'POST'])
def setup_account():
    """If this is the user's first login, the create_or_login function
    will redirect here so that the user can set up his profile.
    """
    if g.user is not None or 'openid' not in session:
        return redirect(url_for('.index'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        if not name:
            flash(u'Error: you have to provide a name')
        elif '@' not in email:
            flash(u'Error: you have to enter a valid email address')
        else:
            flash(u'Profile successfully created')
            User.get_collection().insert(
                User(name, email, session['openid']))
            return redirect(oid.get_next_url())
    return render_template('setup_account.html', next_url=oid.get_next_url())


@app.route('/account', methods=['GET', 'POST'])
def edit_account():
    """Updates a profile"""
    if g.user is None:
        abort(401)
    form = dict(name=g.user.name, email=g.user.email)
    if request.method == 'POST':
        if 'delete' in request.form:
            User.get_collection().remove(g.user)
            session['openid'] = None
            flash(u'Profile deleted')
            return redirect(url_for('.index'))
        form['name'] = request.form['name']
        form['email'] = request.form['email']
        if not form['name']:
            flash(u'Error: you have to provide a name')
        elif '@' not in form['email']:
            flash(u'Error: you have to enter a valid email address')
        else:
            flash(u'Profile successfully created')
            g.user.name = form['name']
            g.user.email = form['email']
            uid = User.get_collection().save(g.user)
            return redirect(url_for('.edit_account'))
    return render_template('edit_account.html', form=form)


@app.route('/logout')
def logout():
    session.pop('openid', None)
    flash(u'You have been signed out')
    return redirect('/')


@current_app.before_request
def before_request():
    g.user = None
    if 'openid' in session:
        g.user = User.find_one({'openid': session['openid']}, as_obj = True)


@oid.after_login
def create_or_login(resp):
    """This is called when login with OpenID succeeded and it's not
    necessary to figure out if this is the users's first login or not.
    This function has to redirect otherwise the user will be presented
    with a terrible URL which we certainly don't want.
    """
    session['openid'] = resp.identity_url
    user = User.get_collection().find_one({'openid':resp.identity_url})
    if user is not None:
        flash(u'Successfully signed in')
        g.user = User
        return redirect(oid.get_next_url())
    return redirect(url_for('.setup_account', next=oid.get_next_url(),
                            name=resp.fullname or resp.nickname,
                            email=resp.email))
