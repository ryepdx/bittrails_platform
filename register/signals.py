from blinker import Namespace
from flask import url_for, session
from flask.ext.login import login_user, current_user, logout_user
from oauth_provider.models import User, UID
from bson.objectid import ObjectId
from auth.signals import oauth_completed
from auth.auth_settings import TOKENS_KEY
import auth

def update_user(sender, response, access_token):
    # Has this account been connected before?
    uid = auth.APIS[session['realm']].get_uid(session['realm'], response)
    uid_obj = UID.find_one({'uid':'%s:%s' % (session['realm'], uid)})
    
    if not uid_obj:
        if not current_user.is_authenticated():
            user = User()
            user['_id'] = User.insert(user)
        else:
            user = current_user
                
        uid_obj = UID('%s:%s' % (session['realm'], uid), user['_id'])
        uid_obj['_id'] = UID.insert(uid_obj)
    else:
        user = User(**User.find_one({'_id':uid_obj['user_id']}))
    
    user['external_tokens'][session['realm']] = access_token
    User.save(user)
    
    # Checking current_user since user is indeed an authenticated user.
    if not current_user.is_authenticated():
        login_user(user)

def load_user(user_id):
    return User(**(User.find_one(ObjectId(user_id))))

def connect_signals(app):
    signals = Namespace()
    #user_registered = signals.signal('register.user_registered')
    #user_registered.connect(send_confirmation_email)

    auth.signals.oauth_completed.connect(update_user)
    app.login_manager.user_loader(load_user)
