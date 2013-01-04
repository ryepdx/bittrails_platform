import pymongo
import json
import datetime
import time
from flask import abort, request
from async_tasks.models import PostsCount
from oauth_provider.models import User, AccessToken, UID

OAUTH_PARAMS = [
    'oauth_version', 'oauth_token', 'oauth_nonce', 'oauth_timestamp',
    'oauth_signature', 'oauth_consumer_key', 'oauth_signature_method'
]
DATE_FORMATS = {
    'y-m-d': (lambda x: x.strftime('%Y-%m-%d')),
    'timestamps': (lambda x: int(time.mktime(x.timetuple())))
}

def get_posts_count_func(user, service, param_path):        
    param_list = param_path.split('/')
    params = dict(
        [(param_list[i*2], param_list[(i*2)+1])
         for i in range(0, len(param_list)/2)])
    
    now = datetime.datetime.utcnow()
    interval = params.get('by', 'week')
    begin = params.get('from', (now - datetime.timedelta(days=30)))
    end = params.get('to', now)
    date_format = DATE_FORMATS.get(
        params.get('as', 'y-m-d').lower(), DATE_FORMATS['y-m-d'])
    
    results = PostsCount.get_collection().find({
            'interval': interval, 'interval_start': {'$gte': begin, '$lte': end},
            'datastream': service, 'user_id': user['_id']
        }).sort('interval_start', direction = pymongo.ASCENDING)
    
    # Modify so that it returns entries for the last 10 intervals,
    # rather than the last 10 entries.
    
    return json.dumps(dict((
        (date_format(result['interval_start']), result['posts_count'])
        for result in results
    )))

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
