from flask import Blueprint, request
from datetime import datetime
import auth.signals
from flask.ext.login import current_user
from auth import APIS
from oauth_provider.models import User, AccessToken
from oauth_provider.views import PROVIDER
from oauthlib.common import add_params_to_uri

OAUTH_PARAMS = [
    'oauth_version', 'oauth_token', 'oauth_nonce', 'oauth_timestamp',
    'oauth_signature', 'oauth_consumer_key', 'oauth_signature_method'
]

app = Blueprint('api', __name__)

@app.route('/correlate')
def correlate():
    date_format = '%Y-%m-%d %H'
    datastreams = {}
    raw_streams = session.get('datastreams')
    
    streams = raw_streams.keys()
    max_date = None
    min_date = None
    hours = []

    for key in streams:
        stream = streams[key]
        first_date = datetime.strptime(stream[0], '%Y-%m-%d %H:%M:%S')
        last_date = datetime.strptime(stream[len(stream)], '%Y-%m-%d %H:%M:%S')
        
        if max_date < last_date or max_date == None:
            max_date = last_date
            
        if min_date > first_date or min_date == None:
            min_date = first_date
    
    counts_blank = {max_date.strftime(date_format): 0}
    while max_date > min_date:
        max_date = max_date - timedelta(hours=1)
        counts_blank[max_date.strftime(date_format)] = 0 
        

def register_apis(apis):
    
    @app.route('/<service>/<path:endpoint>')
    def secondary_api(service, endpoint):
        def passthrough(service, endpoint):
            if request.method ==  "GET":
                token_key = request.args.get('oauth_token')
            elif request.method == "POST":
                token_key = request.form.get('oauth_token')
                
            token = AccessToken.find_one({'token': token_key})
            
            if token:
                token = AccessToken(**token)
                user = User.find_one({'_id': token['user_id']})
                                
                if request.args:
                    params = filter(
                        lambda param: param[0] not in OAUTH_PARAMS,
                        request.args.items())
                    endpoint = add_params_to_uri(endpoint, params)
                        
                if request.method == 'GET':
                    api_call = APIS[service].get(endpoint, user = user)
                elif request.method == 'POST':
                    api_call = APIS[service].post(
                        endpoint,
                        user = user,
                        data = filter(
                            lambda param: param[0] not in OAUTH_PARAMS,
                            request.form.items()
                        )
                    )
                else:
                    abort(400)
            else:
                abort(400)
            
            return api_call.response.content
        return PROVIDER.require_oauth(
            realm = service)(passthrough)(service, endpoint)
        
auth.signals.services_registered.connect(register_apis)
