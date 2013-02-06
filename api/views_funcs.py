import pymongo
import json
import datetime
import time
import collections
import async_tasks.models
from correlations import utils
from correlations.correlationfinder import CorrelationFinder
from flask import abort, request
from oauth_provider.models import User, AccessToken, UID
from oauthlib.common import add_params_to_uri
from auth import APIS

OAUTH_PARAMS = [
    'oauth_version', 'oauth_token', 'oauth_nonce', 'oauth_timestamp',
    'oauth_signature', 'oauth_consumer_key', 'oauth_signature_method'
]
DATE_FORMATS = {
    'y-m-d': (lambda x: x.strftime('%Y-%m-%d')),
    'timestamps': (lambda x: int(time.mktime(x.timetuple())))
}

def increment_time(datetime_obj, interval_name):
    if interval_name == 'day':
        datetime_obj = datetime_obj + datetime.timedelta(days=1)
    
    elif interval_name == 'week':
        datetime_obj = datetime_obj + datetime.timedelta(days=7)
    
    elif interval_name == 'month':
        month = datetime_obj.month + 1
        year = datetime_obj.year
        
        if month > 12:
            month = month % 12
            year = year + 1
        datetime_obj = datetime.datetime(year, month, 1)
            
    elif interval_name == 'year':
        datetime_obj = datetime.datetime(
            datetime_obj.year + 1, 1, 1)
            
    return datetime_obj

def get_service_data_func(user, service, aspect, model_name, request):        
    if hasattr(async_tasks.models, model_name.title()):
        model_class = getattr(async_tasks.models, model_name.title())
    else:
        abort(404)
    
    now = datetime.datetime.utcnow()
    now = datetime.datetime(now.year, now.month, now.day)
    interval = request.args.get('interval', 'week')
    
    begin = model_class.get_start_of(interval, request.args.get(
        'start', (now - datetime.timedelta(days=30))))
    end = request.args.get('end', now)
    date_format = DATE_FORMATS.get(
        request.args.get('timeformat', 'y-m-d').lower(), DATE_FORMATS['y-m-d'])

    results = model_class.get_collection().find({
            'interval': interval, 'start': {'$gte': begin, '$lte': end},
            'datastream': service, 'user_id': user['_id'], 'aspect': aspect
        }).sort('start', direction = pymongo.ASCENDING)
    
    result_data = dict((
        (date_format(result['start']), model_class.get_data(result))
        for result in results
    ))
    
    # Modify so that it returns entries for the last few intervals,
    # rather than the last few entries.
    data = collections.OrderedDict()

    while begin < end:
        key = date_format(begin)
        data[key] = result_data.get(key, 0)
        begin = increment_time(begin, interval)    
    
    return json.dumps(data)
    
def get_correlations(user, aspects_json, start, end, window_size, thresholds,
intervals, model_module = async_tasks.models, use_cache = True):
    correlations = {}
    aspect_tuples = {}
    
    # Create our aspect tuples dictionary for passing on to CorrelationFinder.
    for key in aspects_json:
        aspect_tuples[key] = (
            [utils.aspect_name_to_tuple(aspect, model_module = model_module
            ) for aspect in aspects_json[key]])
    
    finder = CorrelationFinder(user, aspect_tuples,
        start = start, end = end, window_size = window_size,
        thresholds = thresholds, intervals = intervals,
        aspects_json = aspects_json, use_cache = use_cache)
    
    # Filter out all the fields we don't want to include
    # in the returned correlations.
    for interval, correlation_list in finder.get_correlations().items():
        if interval not in correlations:
            correlations[interval] = []
        
        for correlation in correlation_list:
            correlations[interval].append(collections.OrderedDict(
                [(key, correlation[key]) for key in [
                'interval', 'start', 'end','correlation', 'aspects']]))
    
    return correlations

def passthrough(user, apis, service, endpoint):
    if request.args:
        params = filter(
            lambda param: param[0] not in OAUTH_PARAMS,
            request.args.items())
        endpoint = add_params_to_uri(endpoint, params)
            
    if request.method == 'GET':
        api_call = apis[service].get(endpoint, user = user)
    elif request.method == 'POST':
        api_call = apis[service].post(
            endpoint,
            user = user,
            data = filter(
                lambda param: param[0] not in OAUTH_PARAMS,
                request.form.items()
            )
        )
    else:
        abort(400)
    
    return api_call.response.content
