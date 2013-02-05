import json
import numpy
import async_tasks.models
from decimal import Decimal
        
def create_correlation_json(threshold, interval, start, end, correlation):
    return [threshold,
        {'interval': interval, 
         'start': start,
         'end': end,
         'correlation': correlation
        }]
    
def correlate(matrix):
    # Return the correlation strength between the two variables.
    # This number will be found in the lower left-hand corner of the
    # returned correlation matrix.
    try:
        return numpy.corrcoef(matrix)[-1][0]
        
    except FloatingPointError:
        # We get floating point errors when matrices contain identical rows.
        # If that's the case here, we should just return 1.
        # If it's not, pass the error on.
        if matrix.count(matrix[0]) == len(matrix):
            return 1
        else:
            raise

def gatekeeper_func(threshold):
        threshold_num = Decimal(threshold[1:])
            
        if threshold[0] == '<':
            return (lambda x: threshold if x < threshold_num else None)
            
        elif threshold[0] == '>':
            return (lambda x: threshold if x > threshold_num else None)
            
def get_intersection_of_keys(list_of_dicts):
    if list_of_dicts:
        keys = sorted(reduce((
            lambda x, y: x & set(y.keys())), list_of_dicts,
                set(list_of_dicts[0].keys())))
    else:
        keys = []
    
    return keys

def aspect_name_to_tuple(aspect_string, model_module = async_tasks.models):
    aspect, aspect_class = aspect_string.rsplit('_', 1)
    aspect_class = getattr(
        model_module, aspect_class.title())
        
    return (aspect, aspect_class)

def aspect_tuple_to_name(aspect_tuple):
    return aspect_tuple[0] + '_' + aspect_tuple[1].__name__.lower()
