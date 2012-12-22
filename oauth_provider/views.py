import app as core
from flask import Blueprint, request, current_app
from provider import BitTrailsProvider
from models import AccessToken, User
from auth.signals import services_registered

app = Blueprint('oauth_provider', __name__, template_folder='templates')

PROVIDER = BitTrailsProvider(current_app)
PROVIDER.init_blueprint(app)

# Imported to setup views
import login

@app.route('/callback')
def callback():
    return str(request.__dict__)

@app.route("/protected")
@PROVIDER.require_oauth()
def protected_view():
    token = request.oauth.resource_owner_key
    access_token = AccessToken.get_collection().find_one({'token':token})
    user = User.find_one({'_id':access_token['resource_owner_id']})
    return user['name']


@app.route("/protected_realm")
@PROVIDER.require_oauth(realm="secret")
def protected_realm_view():
    token = request.oauth.resource_owner_key
    access_token = AccessToken.get_collection().find_one({'token':token})
    user = User.find_one({'_id':access_token['resource_owner_id']})
    return user['email']
