import app as core
from flask import Blueprint, request, current_app
from provider import BitTrailsProvider
from models import AccessToken
app = Blueprint('oauth_provider', __name__, template_folder='templates')

provider = BitTrailsProvider(current_app)
provider.init_blueprint(app)

# Imported to setup views
import login


@app.route("/protected")
@provider.require_oauth()
def protected_view():
    token = request.oauth.resource_owner_key
    user = AccessToken.get_collection().find_one({'token':token}).resource_owner
    return user.name


@app.route("/protected_realm")
@provider.require_oauth(realm="secret")
def protected_realm_view():
    token = request.oauth.resource_owner_key
    user = AccessToken.get_collection().find_one({'token':token}).resource_owner
    return user.email
