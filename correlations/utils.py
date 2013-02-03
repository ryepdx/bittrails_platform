import numpy
from decimal import Decimal
        
def create_correlation_json(threshold, interval, start, end, correlation):
    return [threshold,
        {'interval': interval, 
         'interval_start': start,
         'interval_end': end,
         'correlation': correlation
        }]
    
def correlate(matrix):
    # Return the correlation strength between the two variables.
    # This number will be found in the lower left-hand corner of the
    # returned correlation matrix.
    return numpy.corrcoef(matrix)[-1][0]

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
