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
from async_tasks.models import (TimeSeriesPath, TimeSeriesData,
    LastCustomDataPull)
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
    

def get_top_level_directory(token, url_prefix):
    user = User.find_one({'_id': token['user_id']})
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
        
    links.update({datastream['name']: {
            'href': '%s/%s.json' % (url_prefix, datastream['name'])
        } for datastream in TimeSeriesPath.get_collection().find(
            {'parent_path': None,
             'user_id': token['user_id'],
             'client_id': token['client_id']
             }
        )
    })
    return json.dumps({'_links': links})


def get_directory(user, parent_path):
    # TODO: Add realm protection.
    url_prefix = request.url_root + 'v1'
    links = {'self': {'href': request.base_url}}
    
    # Check to make sure the requested path exists.
    path_parts = parent_path.strip('/').rsplit('/', 1)
    
    if len(path_parts) > 1:
        parent_path = path_parts[0]
        name = path_parts[1]
        requested_path = TimeSeriesPath.find({'user_id': user['_id'],
            'parent_path': parent_path, 'name': name })
    else:
        parent_path = None
        name = path_parts[0]
        
        # Top level directories don't have specific users associated with them.
        # Instead we go off of the external_tokens dict.
        if name in user['external_tokens'].keys():
            requested_path = TimeSeriesPath.find({
                'parent_path': {'$exists': False}, 'name': name })
        else:
            requested_path = None
            
    
    if requested_path and requested_path.count() > 0:
        
        # Get all the timeseries paths that have the specified parent path.
        for path in TimeSeriesPath.get_collection().aggregate([
        {'$match': {"user_id": user['_id'], "parent_path": parent_path}},
        {'$group': {'_id': {'name':'$name', 'title':'$title'}}}])['result']:
            links[path['_id']['name']] = { 'href': '%s/%s.json' % (url_prefix,
            parent_path if parent_path else '' + path['_id']['name'])
            }
            
            # Include the title in the returned data if the path has one set.
            if 'title' in path['_id']:
                links[path['_id']['name']]['title'] = path['_id']['title']
            
        return json.dumps({'_links': links})
        
    else:
        abort(404)

def get_service_data_func(user, parent_path, leaf_name, request,
query_class = UserTimeSeriesQuery):
    # Check for the last complete pull of the requested data.
    # If the data has not been pulled yet, say so.
    if LastCustomDataPull.find(
    {'path': parent_path.strip('/')+'/', 'user_id': user['_id']}).count() == 0:
        abort(404)         
    
    # Get the parent's title.
    if '/' in parent_path.strip('/'):
        grandparent_path, parent_name = tuple(parent_path[0:-1].rsplit('/', 1))
        parent_title = TimeSeriesPath.get_collection().find(
            {'parent_path': grandparent_path+'/', 'name': parent_name}
        ).distinct('title')
        parent_title = parent_title[0] if len(parent_title) > 0 else None
    else:
        parent_title = None

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

    query = query_class(user, parent_path, leaf_name, match = match,
        group_by = group_by, aggregate = aggregate, min_date = min_date,
        max_date = max_date, sort = sort, continuous = json.loads(
            request.args.get('continuous', 'false')))
    
    try:
        links = {'self': {'href': request.base_url}}
        if parent_title:
            links['self']['title'] = '%s %s' % (leaf_name[0:-1], parent_title)
        
        return json.dumps({
            '_links': links,
            'data': query.get_data()
        })
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
