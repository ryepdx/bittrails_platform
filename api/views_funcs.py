import pymongo
import json
import datetime
import time
import collections
from flask import abort, request
from async_tasks.models import Count
from oauth_provider.models import User, AccessToken, UID
from oauthlib.common import add_params_to_uri

OAUTH_PARAMS = [
    'oauth_version', 'oauth_token', 'oauth_nonce', 'oauth_timestamp',
    'oauth_signature', 'oauth_consumer_key', 'oauth_signature_method'
]
DATE_FORMATS = {
    'y-m-d': (lambda x: x.strftime('%Y-%m-%d')),
    'timestamps': (lambda x: int(time.mktime(x.timetuple())))
}

def increment_time(datetime_obj, interval_name):
    #import pdb; pdb.set_trace()
    if interval_name == 'day':
        datetime_obj = (Count.get_day_start(datetime_obj)
            + datetime.timedelta(days=1))
    
    elif interval_name == 'week':
        datetime_obj = (Count.get_week_start(datetime_obj)
            + datetime.timedelta(days=7))
    
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

def get_post_counts_func(user, service, param_path):        
    param_list = param_path.split('/')
    params = dict(
        [(param_list[i*2], param_list[(i*2)+1])
         for i in range(0, len(param_list)/2)])
    
    now = datetime.datetime.utcnow()
    now = datetime.datetime(now.year, now.month, now.day)
    interval = params.get('by', 'week')
    
    begin = Count.get_start_of(interval, params.get(
        'from', (now - datetime.timedelta(days=30))))
    end = params.get('to', now)
    date_format = DATE_FORMATS.get(
        params.get('as', 'y-m-d').lower(), DATE_FORMATS['y-m-d'])
    
    results = Count.get_collection().find({
            'interval': interval, 'interval_start': {'$gte': begin, '$lte': end},
            'datastream': service, 'user_id': user['_id']
        }).sort('interval_start', direction = pymongo.ASCENDING)
    
    result_counts = dict((
        (date_format(result['interval_start']), result['posts_count'])
        for result in results
    ))
    
    # Modify so that it returns entries for the last few intervals,
    # rather than the last few entries.
    counts = collections.OrderedDict()

    while begin < end:
        key = date_format(begin)
        counts[key] = result_counts.get(key, 0)
        begin = increment_time(begin, interval)    

    return json.dumps(counts)

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
