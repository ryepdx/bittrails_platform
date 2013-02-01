import auth.signals
import json
import decorators

from flask import Blueprint, request, abort
from datetime import datetime
from flask.ext.login import current_user
from auth import APIS
from oauth_provider.models import User, AccessToken
from oauth_provider.views import PROVIDER
from views_funcs import get_service_data_func, passthrough

app = Blueprint('api', __name__)

@app.route('/bittrails/correlate/<service1>/<aspect1>_<model_name1>/with/<service2>/<aspect2>_<model_name2>/by/<interval>')
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

@app.route('/bittrails/<service>/<aspect>_<model_name>s/<path:param_path>')
def get_service_data(service, aspect, model_name, param_path):
    return decorators.provide_oauth_user(
            PROVIDER.require_oauth(realm = service)(get_service_data_func)
        )(service, aspect, model_name, param_path)
        

def register_apis(apis):
    
    @app.route('/<service>/<path:endpoint>')
    def secondary_api(service, endpoint):
        return decorators.provide_oauth_user(
                PROVIDER.require_oauth(realm = service)(passthrough)
            )(apis, service, endpoint)
            
            
    @app.route('/bittrails/datastreams')
    def datastreams():
        return json.dumps(dict([
            (key, {'aspects': value.get_aspects()})
            for key, value in APIS.items()
        ]))
        
auth.signals.services_registered.connect(register_apis)
