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
from correlations.helper_classes import CorrelationJSONEncoder
from flask import abort, request
from oauth_provider.models import User, AccessToken, UID
from oauthlib.common import add_params_to_uri
from auth import APIS
from async_tasks.models import TimeSeriesPath, TimeSeriesData
from async_tasks.helper_classes import (
    UserTimeSeriesQuery, PathNotFoundException)

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
    

def get_top_level_directory(user, url_prefix):
    links = {
        'self': {'href': request.base_url, 'title': 'API root'},
        'dimensions.json': {
            'href': '%s/dimensions.json' % (url_prefix),
            'title': 'dimensions for aggregating leaf data'
        }
    }
        
    links.update({datastream: {
            'href': '%s/%s.json' % (url_prefix, datastream)
        } for datastream in user['external_tokens'].keys()})
    return json.dumps({'_links': links})


def get_directory(user, parent_path):
    url_prefix = request.url_root + 'v1'
    links = {'self': {'href': request.base_url}}
        
    # Get all the timeseries paths that have the specified parent path.
    for path in TimeSeriesPath.get_collection().aggregate([
    {'$match': {"user_id": user['_id'], "parent_path": parent_path}},
    {'$group': {'_id': {'name':'$name', 'title':'$title'}}}])['result']:
        links[path['_id']['name']] = {
            'href': '%s/%s.json' % (url_prefix, path['_id']['name'])
        }
        
        # Include the title in the returned data if the path has one set.
        if 'title' in path['_id']:
            links[path['_id']['name']]['title'] = path['_id']['title']
            
    return json.dumps({'_links': links})

def get_service_data_func(user, path, request,
query_class = UserTimeSeriesQuery):
    # Query parameters.
    match = json.loads(request.args.get('match', '{}'))
    aggregate = json.loads(request.args.get('aggregate', 'null'))
    group_by = json.loads(request.args.get('groupBy', 'null'))
    
    if group_by:
        sort = [(field, pymongo.ASCENDING) for field in group_by]
    else:
        group_by = TimeSeriesData.dimensions
    
    # Calculate the min_date and max_date parameters
    timestamp_match = {}
    min_date = request.args.get('minDate')
    if min_date:
        try:
            min_date = iso8601.parse_date(min_date)
        except iso8601.ParseError:
            min_date = datetime.datetime.strptime(
                min_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
        
    max_date = request.args.get('maxDate')
    if max_date:
        try:
            max_date = iso8601.parse_date(max_date)
        except ParseError:
            max_date = datetime.datetime.strptime(
                max_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
        
    sort = json.loads(
        request.args.get('sort', '{"year":1, "month":1, "week":1, "day":1}'),
        object_pairs_hook = collections.OrderedDict)

    query = query_class(user, path, match = match,
        group_by = group_by, aggregate = aggregate, min_date = min_date,
        max_date = max_date, sort = sort, continuous = json.loads(
            request.args.get('continuous', 'false')))
    
    try:
        return json.dumps(query.get_data())
    except PathNotFoundException:
        abort(404)

def get_correlations(user, paths, group_by, start, end, sort, window_size,
thresholds, use_cache = True):    
    finder = CorrelationFinder(user, paths, group_by = group_by, start = start,
        end = end, sort = sort, window_size = window_size,
        thresholds = thresholds, use_cache = use_cache)
    correlations = [correlation.json_filter()
        for correlation in finder.get_correlations()]
        
    return json.dumps(correlations)

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
