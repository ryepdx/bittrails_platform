import numpy
import logging
import async_tasks.models
from collections import OrderedDict
from api import INTERVALS
from decimal import Decimal
from .settings import MINIMUM_DATAPOINTS_FOR_CORRELATION

def get_matrix_for_correlation(user, required_aspects):
    # Create a dictionary of interval keys to dictionaries of
    # datastream keys to empty dictionaries.
    data = dict([(interval, []) for interval in INTERVALS])
    
    # Get the data corresponding to every aspect required.
    for datastream in required_aspects:
        for aspect_string in required_aspects[datastream]:
            aspect, aspect_class = aspect_string.rsplit('_', 1)
            aspect_class = getattr(
                async_tasks.models, aspect_class.title())
            data_history = dict(
                [(interval, OrderedDict()) for interval in INTERVALS]) 
            
            # And get the data for that aspect for every interval.
            datapoints = aspect_class.get_collection().find(
                {'user_id': user['_id'], 'datastream': datastream,
                 'aspect': aspect}).sort('interval_start', -1)
                 
            # Cycle through the datapoints and separate them by interval
            for row in datapoints:                        
                data_history[row['interval']][row['interval_start']] = (
                    aspect_class.get_data(row))
                    
            # Add the data dictionaries for each interval.
            for key, item in data_history.items():
                data[key].append(item)

    return data

def gatekeeper_func(threshold):
    threshold_num = Decimal(threshold[1:])
        
    if threshold[0] == '<':
        def lt_gatekeeper(correlation):
            return threshold if correlation < threshold_num else None
            
        return lt_gatekeeper
        
    elif threshold[0] == '>':
        def gt_gatekeeper(correlation):
            return threshold if correlation > threshold_num else None
            
        return gt_gatekeeper


def find_correlations(user, data, thresholds = None, 
minimum_datapoints = MINIMUM_DATAPOINTS_FOR_CORRELATION):
        correlations = []
        
        if not thresholds:
            gatekeepers = [(lambda x: 'no thresholds specified')]
        else:
            gatekeepers = []
            
            for threshold in thresholds:
                try:
                    gatekeepers.append(gatekeeper_func(threshold))
                    
                except:
                    raise Exception("Error parsing threshold: %s" % threshold)
        
        for interval, datastream_list in data.items():
            # Right now we're just assuming that there is no data available
            # for a datapoint if there is no entry for it.
            # TODO: Make missing datapoints imply 0 for continuous datastream
            # aspects like Twitter and Last.fm counts.            
            if datastream_list:
                interval_keys = sorted(reduce((
                    lambda x, y: x & set(y.keys())), datastream_list,
                        set(datastream_list[0].keys())))
            else:
                interval_keys = []
            
            # Make sure we have enough overlapping datapoints
            # to find a correlation.
            if len(interval_keys) >= minimum_datapoints:
                datapoints_list = [OrderedDict() for i in range(
                    0, len(datastream_list))]
                correlation = 0
                activated_threshold = None
                current_threshold = None
                covered_interval_keys = []
                
                for key in interval_keys:
                    for i, datastream in enumerate(datastream_list):
                        datapoints_list[i][key] = datastream[key]
                    
                    # Make sure there are enough datapoints in our sliding
                    # window to find a correlation.
                    if len(datapoints_list[0]) >= minimum_datapoints:
                        last_correlation = correlation
                        activated_threshold = None
                        
                        try:
                            correlation = correlate([datapoint.values(
                                ) for datapoint in datapoints_list])
                            
                            for gatekeeper in gatekeepers:
                                if not activated_threshold:
                                    activated_threshold = gatekeeper(correlation)
                                else:
                                    break
                                    
                        except Exception as err:
                            logging.error(("Error while finding correlations " 
                                + "for user %s." % user['_id']),
                                exc_info = err)

                        # Didn't find a correlation and we're not carrying
                        # forward a correlation?
                        if not activated_threshold and not current_threshold:
                            # Slide the window forward.
                            datapoints_list = [
                                    OrderedDict(datapoints_list[i].items()[1:]
                                    ) for i in range(0, len(datapoints_list))] 
                        
                        # Were we trying to accumulate datapoints when the
                        # template key went away or changed? Then save the buff.
                        # We want to save the start of the last interval the
                        # buff was applicable to as that buff's end, so we grab
                        # the date *before* the date of the last datapoint, as
                        # the last datapoint caused the correlation to end.
                        elif activated_threshold != current_threshold:
                            if current_threshold:
                                correlations.append([current_threshold,
                                    {'interval': interval, 
                                     'interval_start':
                                            datapoints_list[0].keys()[0],
                                     'interval_end':
                                            datapoints_list[0].keys()[-2],
                                     'correlation': last_correlation
                                    }]
                                )
                                
                                datapoints_list = [
                                    OrderedDict(datapoints_list[i].items()[-1:]
                                    ) for i in range(0, len(datapoints_list))]                                             
                                
                            # Either way, update current_threshold.
                            current_threshold = activated_threshold
                            
                
                # If a threshold was passed, then there was a significant
                # correlation found. Register a correlation.
                if current_threshold:
                    correlations.append([current_threshold,
                        {'interval': interval, 
                         'interval_start': datapoints_list[0].keys()[0],
                         'interval_end': datapoints_list[0].keys()[-2],
                         'correlation': last_correlation
                        }
                    ])
                    
        return correlations
    
def correlate(matrix):
    # Return the correlation strength between the two variables.
    # This number will be found in the lower left-hand corner of the
    # returned correlation matrix.
    return numpy.corrcoef(matrix)[-1][0]
