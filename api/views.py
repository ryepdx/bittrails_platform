from flask import Blueprint, request
from datetime import datetime
import auth.signals

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
        if request.method == 'GET':
            api_call = apis[service].get(endpoint)
        elif request.method == 'POST':
            api_call = apis[service].post(endpoint, data = request.form)
        
        return api_call.response.content
        
auth.signals.services_registered.connect(register_apis)
