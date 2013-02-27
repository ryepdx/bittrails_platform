import pymongo
import logging
import async_tasks.models
import utils
from async_tasks.models import Correlation
from collections import OrderedDict
from api.constants import INTERVALS
from decimal import Decimal
from constants import MINIMUM_DATAPOINTS_FOR_CORRELATION
from async_tasks.helper_classes import UserTimeSeriesQuery

class CorrelationFinder(object):
    def __init__(self, user, paths, match = None, group_by = None,
    start = None, end = None, sort = None,
    window_size = MINIMUM_DATAPOINTS_FOR_CORRELATION,
    thresholds = [], use_cache = False):
        self.user = user
        self.paths = paths
        self.match = match
        self.group_by = group_by
        self.start = start
        self.end = end
        self.sort = sort
        self.window_size = window_size
        self.thresholds = thresholds
        self.gatekeepers = self._create_gatekeepers(thresholds)
        self.use_cache = use_cache
        
    def get_correlations(self):
        results = {}
        correlation_key = self.generate_correlation_key()
        
        if self.use_cache:
            # First find out if we've cached any of these correlations.
            # We're only interested if we cached a correlation with exactly the
            # requested parameters beginning on exactly the day requested.
            # Otherwise all correlations following it could be off, given that
            # we're starting at a different offset.
            correlations = self.retrieve_cache(correlation_key)
        else:
            correlations = []
        
        # Alright, let's find whatever correlations there are left to find!
        # Are there gaps between the end of the cache and the end of the
        # requested timeframe that we need to fill in here?
        if (self.use_cache and correlations):
            matrix = self.get_matrix(start = correlations[-1]['end'])
        else:
            matrix = self.get_matrix()
        
        covered_timeframes = matrix[0]
        matrix = matrix[1:]
        
        # Make sure we have enough datapoints to find a correlation.
        if len(covered_timeframes) >= self.window_size:
            results = self.find_correlations(matrix, covered_timeframes)

            if self.use_cache:
                # Cache all the results (except for the last one if the
                # last one appears to only have had its end date set by
                # virtue of running out of data.)
                if (results
                and results[-1]['end'] == covered_timeframes[-1]):
                    results[key].pop()
        
                self.cache_correlations(results, correlation_key)
            
            correlations += results
                
        return correlations
        
    # Broke this out into its own function so we can override it for testing.
    def cache_correlations(self, correlations, correlation_key):
        for correlation in correlations:
            correlation.user_id = self.user['_id']
            correlation.key = correlation_key
            correlation.save()
            
    def retrieve_cache(self, correlation_key):
        correlations = []
        params = {'key': correlation_key}
        
        if self.start:
            params['start'] = {'$gte': start}
        
        if self.end:
            params['end'] = {'$lte': self.end}
                
        #cache = [row for row in Correlation.get_collection().find(params
        #    ).sort('start', pymongo.ASCENDING)]
            
        
        cache = Correlation.get_collection().find(params
            ).sort('start', pymongo.ASCENDING)
        
        for row in cache:
            correlations.append(Correlation(**row))
        
        return correlations

    def generate_correlation_key(self):
        '''
        Takes a dictionary of lists of aspect names with service names as the
        keys. Returns the value saved in the 'key' field for the correlation
        using that set of aspects.
        '''
        return ''.join([
            str(self.start),
            str(self.window_size),
            ':'.join(sorted(self.paths)),
            ','.join(sorted(self.group_by)),
            ','.join(sorted(self.sort.keys())),
            ','.join([str(value) for value in sorted(self.sort.values())]),
            ','.join(sorted(self.thresholds))
        ])

    def get_path_data(self, start = None, end = None):
        '''
        Create a list of dictionaries, one for each requested aspect,
        mapping interval start dates to datapoints.
        '''
        path_data = []
        
        if not start:
            start = self.start
            
        if not end:
            end = self.end
            
        # Get the data corresponding to every aspect required.
        for path in self.paths:            
            # And get the data for that aspect for every interval.
            query = UserTimeSeriesQuery(self.user, path, match = self.match,
                group_by = self.group_by, min_date = self.start,
                sort = self.sort, max_date = self.end)
            datapoints = query.get_data()
            
            path_data.append(OrderedDict([
                (str([row[field] for field in self.group_by]), row['value']
                ) for row in datapoints]))

        return path_data

    def get_matrix(self, start = None, end = None, path_data = None,
    covered_timeframes = None):
        '''
        Create a list of dictionaries, one for each requested aspect,
        mapping interval start dates to datapoints.
        '''
        data = []
        
        if not path_data:
            path_data = self.get_path_data()

        if not covered_timeframes:                
            covered_timeframes = list(reduce(
                lambda x, y: [key for key in y.keys() if key in x.keys()],
                [datapoints for datapoints in path_data]))
        
        data.append(covered_timeframes)    
        
        for datapoints in path_data:
            data.append([])
            
            for timeframe in covered_timeframes:
                data[-1].append(datapoints[timeframe])
        
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
        
    def find_correlations(self, matrix, timestamps):
        correlations = []
        correlation = 0
        activated_threshold = None
        current_threshold = None
        window_start = 0
        window_end = self.window_size
        matrix_row_len = len(matrix[0])
        
        # Make sure there are enough datapoints in our sliding
        # window to find a correlation.
        if matrix_row_len >= self.window_size:
            last_correlation = correlation
            activated_threshold = None
            
            while window_end < matrix_row_len:
                try:
                    activated_threshold = None
                    correlation = utils.correlate(
                        [stream[window_start:window_end] for stream in matrix])
                    
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
                    window_start += 1
                    window_end += 1
                
                # Were we trying to accumulate datapoints when the
                # correlation went away or changed? Then save the buff.
                # We want to save the start of the last interval the
                # buff was applicable to as that buff's end, so we grab
                # the date *before* the date of the last datapoint, as
                # the last datapoint caused the correlation to end.
                elif activated_threshold != current_threshold:
                    
                    # If we were extending out a correlation, then it must have
                    # just dropped below the threshold. Save it and start the
                    # window over.
                    if current_threshold:
                        correlations.append(Correlation(
                            user_id = self.user['_id'],
                            threshold = current_threshold,
                            paths = self.paths,
                            group_by = self.group_by,
                            sort = self.sort,
                            start = timestamps[window_start],
                            end = timestamps[window_end - 1],
                            correlation = last_correlation,
                            key = self.generate_correlation_key())
                        )
                        
                        window_start = window_end
                        window_end = window_start + self.window_size
                        
                    # Either way, update current_threshold.
                    current_threshold = activated_threshold
                    
                # Just extending out a correlation?
                elif current_threshold == activated_threshold:
                    window_end += 1
                
        # "if current_threshold," then we were extending out a correlation
        # when we reached the end of the matrix. Save the correlation.
        if current_threshold:
            correlations.append(
                Correlation(
                    user_id = self.user['_id'],
                    threshold = current_threshold,
                    paths = self.paths,
                    group_by = self.group_by,
                    sort = self.sort,
                    start = timestamps[window_start],
                    end = timestamps[window_end-1],
                    correlation = last_correlation,
                    key = self.generate_correlation_key()
                )
            )
        
        return correlations
