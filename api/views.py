import collections
import pytz
import iso8601
import auth.signals
import json
import decorators
import bson
import correlations.jsonencoder
import async_tasks.datastreams.tasks

from collections import OrderedDict
from decimal import Decimal
from flask import Blueprint, request, abort
from datetime import datetime
from flask.ext.login import current_user
from auth import APIS
from oauth_provider.models import User, AccessToken
from oauth_provider.views import PROVIDER
from async_tasks.models import Correlation, TimeSeriesData
from correlations.constants import MINIMUM_DATAPOINTS_FOR_CORRELATION
from views_funcs import (get_service_data_func, get_children_func,
    get_correlations, passthrough)

app = Blueprint('api', __name__)


@app.route('/correlations/<correlation_id>.json')
def correlation(correlation_id):
    try:
        correlation = Correlation.find_one(bson.ObjectId(correlation_id))
        
        if not correlation:
            abort(404)
            
        correlation = OrderedDict([(key, correlation[key]
            ) for key in ['interval', 'start', 'end', 'correlation',
            'aspects']])
            
    except bson.errors.InvalidId:
        abort(404)
        
    protected_func = (lambda x: x)
    
    # Wrap the return function in the appropriate realm checks.
    for datastream in correlation['aspects'].keys():
        protected_funct = PROVIDER.require_oauth(
            realm = datastream)(protected_func)
        
    return protected_func(json.dumps(
            correlation, cls = correlations.jsonencoder.JSONEncoder))


@app.route('/correlations.json')
def find_correlations():
    paths = request.args.get("paths")
    thresholds = request.args.get("thresholds")
    group_by = request.args.get("groupBy")
    window_size = request.args.get(
        "minDatapoints", MINIMUM_DATAPOINTS_FOR_CORRELATION)
    
    try:
        continuous = json.loads(request.args.get("continuous", "false"))
    except:
        continuous = False
    
    # Validate start date parameter
    min_date = request.args.get('minDate')
    if min_date:
        try:
            min_date = iso8601.parse_date(min_date)
        except iso8601.ParseError:
            min_date = datetime.strptime(
                min_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
        
      
    # Validate end date parameter
    max_date = request.args.get('maxDate')
    if max_date:
        try:
            max_date = iso8601.parse_date(max_date)
        except iso8601.ParseError:
            max_date = datetime.strptime(
                max_date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    
        
    # Validate intervals parameter.
    if paths:
        try:
            paths = json.loads(paths)
        except:
            abort(400)
    else:
        abort(400)
        
    # Validate thresholds parameter.
    if thresholds:
        try:
            thresholds = json.loads(thresholds)
            
            # Make sure they are all formatted correctly.
            for threshold in thresholds:
                if threshold[0] not in ['>', '<']:
                    abort(400)
                    
                # Will throw an exception if it's not correctly formatted.
                Decimal(threshold[1:])
                
        except:
            abort(400)
    else:
        abort(400)
    
    # Validate aspects parameter.
    if group_by:
        try:
            group_by = json.loads(group_by)
        except:
            abort(400)
    else:
        abort(400)
        
    # Validate window_size parameter
    try:
        window_size = int(window_size)
        
        if window_size < 2:
            abort(400)
            
    except:
        abort(400)
        
    sort = json.loads(
        request.args.get('sort', '{"year":1, "month":1, "week":1, "day":1}'),
        object_pairs_hook = collections.OrderedDict)
    
    # Wrap our return function in the appropriate realm checks.
    protected_func = (lambda user: json.dumps(
        get_correlations(user, paths, group_by, min_date, max_date, sort,
        window_size, thresholds, use_cache = False),
        cls = correlations.jsonencoder.JSONEncoder))
    # TODO: Fix realm check.
    #for datastream in aspects.keys():
    #    protected_funct = PROVIDER.require_oauth(
    #        realm = datastream)(protected_func)
            
    return decorators.provide_oauth_user(protected_func)()

@app.route('/<path:path>.json')
def get_service_data(path):
    return decorators.provide_oauth_user(
        get_service_data_func)(path, request)
    
    
@app.route('/<path:parent_path>children.json')
def get_children(parent_path):
    return decorators.provide_oauth_user(get_children_func)(parent_path)
        

@app.route('/children.json')
def get_top_level_children():
    # Should eventually get rid of this function and just add top-level path
    # entries when a user authorizes a new service.
    return json.dumps(
        ['children.json', 'groupBy.json'] + [(task_class.datastream_name + "/"
        ) for task_class in async_tasks.datastreams.tasks.Tasks.__subclasses__()])
        
@app.route('/dimensions.json')
def dimensions():
    return json.dumps(TimeSeriesData.dimensions)

def register_apis(apis):
    
    @app.route('/passthrough/<service>/<path:endpoint>')
    def secondary_api(service, endpoint):
        return decorators.provide_oauth_user(
                PROVIDER.require_oauth(realm = service)(passthrough)
            )(apis, service, endpoint)
        
auth.signals.services_registered.connect(register_apis)
