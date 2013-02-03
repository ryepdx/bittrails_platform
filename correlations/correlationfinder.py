import pymongo
import numpy
import logging
import async_tasks.models
import utils
from async_tasks.models import Correlation
from collections import OrderedDict
from api import INTERVALS
from decimal import Decimal
from constants import MINIMUM_DATAPOINTS_FOR_CORRELATION

class CorrelationFinder(object):
    def __init__(self, user, aspects, interval_start = None,
    interval_end = None, window_size = MINIMUM_DATAPOINTS_FOR_CORRELATION,
    thresholds = [], intervals = INTERVALS):
        self.user = user
        self.aspects = aspects
        self.start = interval_start
        self.end = interval_end
        self.window_size = window_size
        self.thresholds = thresholds
        self.gatekeepers = self._create_gatekeepers(thresholds)
        self.intervals = intervals
        
    def get_correlations(self):
        results = {}
        correlation_key = self.generate_correlation_key()
        
        # First find out if we've cached any of these correlations.
        # We're only interested if we cached a correlation with exactly the
        # requested parameters beginning on exactly the day requested.
        # Otherwise all correlations following it could be off, given that
        # we're starting at a different offset.
        correlations = self.retrieve_cache(correlation_key)
        
        # Alright, let's find whatever correlations there are left to find!
        for interval in self.intervals:
            
            # Are there gaps between the end of the cache and the end of the
            # requested timeframe that we need to fill in here?
            if interval in correlations and correlations[interval]:
                matrix = self.get_matrix(interval,
                    correlations[interval][-1]['interval_end'], self.end)
            else:
                matrix = self.get_matrix(interval, self.start, self.end)
            
            # Right now we're just assuming that there is no data available
            # for a datapoint if there is no entry for it.
            # TODO: Make missing datapoints imply 0 for continuous datastream
            # aspects like Twitter and Last.fm counts.            
            interval_keys = utils.get_intersection_of_keys(matrix)
            
            # Make sure we have enough overlapping datapoints
            # to find a correlation.
            if len(interval_keys) >= self.window_size:
                results[interval] = self.find_correlations(
                    matrix, interval, interval_keys)
        
                correlations[interval] += results[interval]
        
                # Cache all the results (except for the last one if the last one
                # appears to only have had its end date set by virtue of running 
                # out of data.)
                if (results[interval] 
                and results[interval][-1]['interval_end'] == interval_keys[-1]):
                    results[key].pop()
            
                self.cache_correlations(results[interval], correlation_key)
            
        return correlations
        
    # Broke this out into its own function so we can override it for testing.
    def cache_correlations(self, correlations, correlation_key):
        for correlation in correlations:
            correlation.user_id = self.user['_id']
            correlation.key = correlation_key
            correlation.save()
            
    def retrieve_cache(self, correlation_key):
        params = {'key': correlation_key}
        correlations = dict([(interval, []) for interval in self.intervals])
        
        has_cache = (self.start == None 
            or async_tasks.models.Correlation.find_one(dict(
            params.items() + [('interval_start', self.start)])))
        
        if has_cache:
            if self.start:
                params['interval_start'] = {'$gte': interval_start}
        
            if self.end:
                params['interval_end'] = {'$lte': self.end}
                
            cache = [row for row in Correlation.get_collection().find(params
                ).sort('interval_start', pymongo.ASCENDING)]
            
            for row in cache:
                correlations[row['interval']].append(Correlation(**row))
        
        return correlations

    def generate_correlation_key(self):
        '''
        Takes a dictionary of lists of aspect names with service names as the
        keys. Returns a key for looking up a correlation.
        '''
        key = [str(self.start) + ' ' + str(self.window_size)]
        aspect_names = []
        for datastream in self.aspects:
            for aspect in self.aspects[datastream]:
                aspect_names.append(datastream + ':' + 
                    utils.aspect_tuple_to_name(aspect))
                    
        key += sorted(aspect_names)
                
        return ','.join(key) + ',' + str(sorted(self.thresholds))

    def get_matrix(self, interval, interval_start, interval_end):
        # Create a dictionary of interval keys to dictionaries of
        # datastream keys to empty dictionaries.
        data = []
        params = {'user_id': self.user['_id'], 'interval': interval}
        
        if interval_start:
            params['interval_start'] = {'$gte': interval_start}
        
        if interval_end:
            params['interval_end'] = {'$lte': interval_end}
        
        # Get the data corresponding to every aspect required.
        for datastream in self.aspects:
            for aspect, aspect_class in self.aspects[datastream]:
                params['datastream'] = datastream
                params['aspect'] = aspect
                
                # And get the data for that aspect for every interval.
                datapoints = aspect_class.get_collection(
                    ).find(params).sort('interval_start', pymongo.ASCENDING)
                
                data.append(OrderedDict([(row['interval_start'],
                    aspect_class.get_data(row)) for row in datapoints]))

        return data

    def _create_gatekeepers(self, thresholds):
        if not thresholds:
            gatekeepers = [(lambda x: 'no thresholds specified')]
        else:
            gatekeepers = []
            
            for threshold in thresholds:
                try:
                    gatekeepers.append(utils.gatekeeper_func(threshold))
                    
                except:
                    raise Exception("Error parsing threshold: %s" % threshold)
                    
        return gatekeepers
        
    def find_correlations(self, datastream_list, interval, interval_keys):
        correlations = []
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
            if len(datapoints_list[0]) >= self.window_size:
                last_correlation = correlation
                activated_threshold = None
                
                try:
                    correlation = utils.correlate([datapoint.values(
                        ) for datapoint in datapoints_list])
                    
                    for gatekeeper in self.gatekeepers:
                        if not activated_threshold:
                            activated_threshold = gatekeeper(correlation)
                        else:
                            break
                    
                except Exception as err:
                    logging.error(("Error while finding correlations " 
                        + "for user %s." % self.user['_id']),
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
                        correlations.append(Correlation(
                            user_id = self.user['_id'],
                            threshold = current_threshold,
                            interval = interval,
                            interval_start = datapoints_list[0].keys()[0],
                            interval_end = datapoints_list[0].keys()[-2],
                            correlation = last_correlation,
                            key = self.generate_correlation_key())
                        )
                        
                        datapoints_list = [
                            OrderedDict(datapoints_list[i].items()[-1:]
                            ) for i in range(0, len(datapoints_list))]                                             
                        
                    # Either way, update current_threshold.
                    current_threshold = activated_threshold
        
        # If a threshold was passed, then there was a significant
        # correlation found. Register a correlation.
        if current_threshold:
            correlations.append(
                Correlation(
                    user_id = self.user['_id'],
                    threshold = current_threshold,
                    interval = interval,
                    interval_start = datapoints_list[0].keys()[0],
                    interval_end = datapoints_list[0].keys()[-2],
                    correlation = last_correlation,
                    key = self.generate_correlation_key()
                )
            )
        
        return correlations
