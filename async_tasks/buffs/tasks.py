import logging
import numpy
from api import INTERVALS
from async_tasks.models import Count, Average
from buffs.models import Buff
from collections import OrderedDict

# By default numpy just raises warnings when it encounters problems.
# I want it to raise exceptions so I can catch and log them.
numpy.seterr(all='raise')

class CorrelationTask(object):
    def __init__(self, user, available_datastreams, logger = None):
        self.user = user
        self.available_datastreams = set(available_datastreams)
        self._logger = logger if logger else logging.getLogger(
            __name__ + '.' + self.__class__.__name__)
        
    @property
    def required_aspects(self):
        raise NotImplemented("Inheriting classes must implement this.")
        
    def get_template_key(self, correlation):
        raise NotImplemented("Inheriting classes must implement this.")
        
    def run(self):
        # Create a dictionary of interval keys to dictionaries of
        # datastream keys to empty dictionaries.
        data = dict([(interval, []) for interval in INTERVALS])
        
        # Do we have the required datastreams to run this correlation?
        if set(self.required_aspects).issubset(self.available_datastreams):
            
            # Get the data corresponding to every aspect required.
            for datastream, (aspect, aspect_class) in self.required_aspects.items():
                
                # And get the data for that aspect for every interval.
                # TODO: Limit this query. It'll get huge pretty quickly.
                # Also, it kinda bothers me that we have a query in a nested
                # 'for' loop! Seems *super* inefficient.
                for interval in INTERVALS:
                    data[interval].append(OrderedDict(
                        [(row['interval_start'], aspect_class.get_data(row))
                            for row in aspect_class.get_collection().find(
                            {'user_id': self.user['_id'],
                             'datastream': datastream,
                             'aspect': aspect,
                             'interval': interval
                            }).sort({'interval_start': -1})
                    ]))
        
        # Okay, now let's look for some correlations!
        self.save_buffs(self.create_buffs(data))
        
    # Broke this out into its own function so we can override it for testing.
    def save_buffs(self, buffs):
        for buff in buffs:
            buff.save()
        
    def create_buffs(self, data):
        buffs = []
        
        for interval, datapoints_list in data.items():
            # Right now we're just assuming that there is no data available
            # for a datapoint if there is no entry for it.
            # TODO: Make missing datapoints imply 0 for continuous datastream
            # aspects like Twitter and Last.fm counts.
            correlation_matrix = []
            interval_keys = list(reduce((
                lambda x, y: x & set(y.keys())), datapoints_list,
                    set(datapoints_list[0].keys())))
                    
            for datapoints_dict in datapoints_list:
                datapoints = []
                
                for key in interval_keys:
                    datapoints.append(datapoints_dict[key])
                    
                correlation_matrix.append(datapoints)
            
            # correlation_matrix should be a list of lists of datapoint values.
            correlation = self.correlate(correlation_matrix)
            template_key = self.get_template_key(correlation)
            
            # If a template key was found, then there was a significant
            # correlation found. Create a buff.
            if template_key:
                buffs.append(
                    Buff(user_id = self.user['_id'],
                         interval = interval,
                         interval_start = interval_keys[0],
                         interval_end = interval_keys[-1],
                         correlation = correlation,
                         aspects = self.required_aspects,
                         template_key = template_key)
                )
            
        return buffs
        
    def correlate(self, matrix):
        # Return the correlation strength between the two variables.
        # This number will be found in the lower left-hand corner of the
        # returned correlation matrix.
        try:
            return numpy.corrcoef(matrix)[-1][0]
        except FloatingPointError as err:
            self._logger.error(("Error while finding correlations " 
                + "for user %s." % self.user['_id']), exc_info = err)
            return 1
        
class LastFmEnergyAndGoogleTasks(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'google_tasks': ('completed_task', Count),
                 'lastfm': ('song_energy', Average)}
                 
    def get_template_key(self, correlation):
        if correlation > 0.5:
            return 'lastfm_and_google_tasks_positive'
        elif correlation < -0.5:
            return 'lastfm_and_google_tasks_negative'
        else:
            return 'lastfm_and_google_tasks_neutral'
