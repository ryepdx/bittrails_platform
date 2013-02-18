import pymongo
import json
import datetime
import time
import collections
import async_tasks.datastreams.handlers
import iso8601
import logging
import pytz
import bson
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

LOGGER = logging.getLogger(__name__)

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
        datetime_obj = datetime.datetime(year, month, 1, tzinfo = datetime_obj.tzinfo)
            
    elif interval_name == 'year':
        datetime_obj = datetime.datetime(
            datetime_obj.year + 1, 1, 1, tzinfo = datetime_obj.tzinfo)
            
    return datetime_obj

def get_service_data_func(user, datastream, aspect, handler_name, request):
    if hasattr(async_tasks.datastreams.handlers, handler_name):
        model_class = getattr(
            async_tasks.datastreams.handlers, handler_name).model_class
    else:
        abort(404)
    
    match = json.loads(request.args.get('match', '{}'))
    dimensions = json.loads(request.args.get('dimensions', 'null'))
    
    now = datetime.datetime.now(pytz.utc).replace(
        hour = 0, minute = 0, second = 0, microsecond = 0)
    interval = request.args.get('interval', 'week')
    
    start = request.args.get('start')
    if start:
        start = iso8601.parse_date(start)
    else:
        start = (now - datetime.timedelta(days=30))        
    start = model_class.get_start_of(interval, start)
    
    end = request.args.get('end')
    if end:
        end = iso8601.parse_date(end)
    else:
        end = now

    date_format = DATE_FORMATS.get(
        request.args.get('timeformat', 'y-m-d').lower(), DATE_FORMATS['y-m-d'])

    match.update(
        {'start': {'$gte': start, '$lte': end}, 'user_id': user['_id'],
         'datastream': datastream, 'aspect': aspect})
        
    aggregation = [{'$match': match}]
    
    grouping = {'_id': {}}
    if dimensions:
        for dimension, aggregator in dimensions.items():
            if aggregator == "identity":
                grouping['_id'][dimension] = '$'+dimension;
            else:
                grouping[dimension] = {'$'+aggregator: '$'+dimension}
        dimensions = dimensions.keys()
    else:
        dimensions = model_class.dimensions
        for dimension in dimensions:
            grouping['_id'][dimension] = '$'+dimension;

    grouping['_id'].update({'start':'$start', 'user_id':'$user_id'})
    
    # Append our preprocessor projection to the aggregation functions.
    pre_projection = dict([(dimension, '$_id.' + dimension
        ) for dimension in grouping['_id'].keys()])
    pre_projection['_id'] = 0
    
    post_projection = dict([(dimension, 1) for dimension in dimensions])
    post_projection.update(dict([(dimension, value
        ) for dimension, value in pre_projection.items() if '_id' not in dimension]))
        
    # Append our preprocessor grouping to the aggregation functions.
    if model_class.extra_grouping:
        pre_grouping = {'_id': grouping['_id']}
        pre_grouping.update(model_class.extra_grouping)
        aggregation.append({'$group': pre_grouping})
        
    if model_class.extra_dimensions:
        pre_projection.update(model_class.extra_dimensions)
        aggregation.append({'$project': pre_projection})
    
    # Okay, now we append the grouping the user requested.
    aggregation.append({'$group': grouping})
    aggregation.append({'$project': post_projection})
    aggregation.append({'$sort': bson.SON([('start', pymongo.ASCENDING)])})
    results = model_class.get_collection().aggregate(aggregation)
    
    result_data = collections.OrderedDict()
    
    for result in results['result']:
        result_start = date_format(result['start'])
        if result_start not in result_data:
            result_data[result_start] = []
                
        result_data[result_start].append(model_class.get_data(result))
    
    # Fill in missing datapoints for "continuous" datastreams (like Twitter.)
    if not model_class.continuous:
        data = result_data
    else:
        data = collections.OrderedDict()

        while start < end:
            key = date_format(start)
            data[key] = result_data.get(
                key, [model_class.get_empty_data(dimensions)])
            start = increment_time(start, interval)
        
    return json.dumps(data)
    
def get_correlations(user, aspects_json, start, end, window_size, thresholds,
intervals, handler_module = async_tasks.datastreams.handlers, use_cache = True):
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
