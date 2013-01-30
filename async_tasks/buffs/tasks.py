import logging
import numpy
from api import INTERVALS
from async_tasks.models import Count, Average
from buffs.models import Buff
from collections import OrderedDict
from .settings import MINIMUM_DATAPOINTS_FOR_CORRELATION

# By default numpy just raises warnings when it encounters problems.
# I want it to raise exceptions so I can catch and log them.
numpy.seterr(all='raise')

class CorrelationTask(object):
    def __init__(self, user, available_datastreams, logger = None):
        self.user = user
        self.available_datastreams = set(available_datastreams)
        self._logger = logger if logger else logging
        
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
            for datastream, (aspect, aspect_class
            ) in self.required_aspects.items():
                data_history = dict(
                    [(interval, OrderedDict()) for interval in INTERVALS]) 
                
                # And get the data for that aspect for every interval.
                datapoints = aspect_class.get_collection().find(
                    {'user_id': self.user['_id'], 'datastream': datastream,
                     'aspect': aspect}).sort('interval_start', -1)
                     
                # Cycle through the datapoints and separate them by interval.
                for row in datapoints:                        
                    data_history[row['interval']][row['interval_start']] = (
                        aspect_class.get_data(row))
                        
                # Add the data dictionaries for each interval.
                for key, item in data_history.items():
                    data[key].append(item)
                        
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
            interval_keys = sorted(reduce((
                lambda x, y: x & set(y.keys())), datapoints_list,
                    set(datapoints_list[0].keys())))
            
            # Make sure we have enough overlapping datapoints
            # to find a correlation.
            if len(interval_keys) >= MINIMUM_DATAPOINTS_FOR_CORRELATION:
                datapoints = [[] for i in range(0, len(datapoints_list))]
                buff_start = None
                buff_template = None
                
                for key in interval_keys: # Cycle through all common dates.
                    for i, datapoints_dict in enumerate(datapoints_list):
                        datapoints[i].append(datapoints_dict[key])
                    
                    if len(datapoints[0]) >= MINIMUM_DATAPOINTS_FOR_CORRELATION:
                        correlation = self.correlate(datapoints)
                        template_key = self.get_template_key(correlation)
                        
                        # Were we trying to walk out a buff when the template
                        # key went away or changed? Then save the buff.
                        if buff_template and template_key != buff_template:
                            buffs.append(
                                self.create_buff(interval, buff_start, key,
                                    correlation, template_key)
                            )
                            buff_start = None
                            buff_template = None
                            datapoints = [[] for i in range(0, len(datapoints_list))]
                            
                        # Was there a buff found for this correlation, and if so,
                        # is it not a buff we're currently walking out?
                        if template_key and template_key != buff_template:
                            buff_start = key
                            buff_template = template_key
                
                # If a template key was found, then there was a significant
                # correlation found. Create a buff.
                if buff_template:
                    buffs.append(self.create_buff(interval, buff_start,
                        interval_keys[-1], correlation, buff_template))
                    
        return buffs
        
        
    def create_buff(self, interval, start, end, correlation, template_key):
        return Buff(
            user_id = self.user['_id'],
            interval = interval,
            interval_start = start,
            interval_end = end, 
            correlation = correlation,
            aspects = dict([(datastream, aspect) for datastream, (aspect, _
                ) in self.required_aspects.items()]),
            template_key = template_key)
        
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
            return 'lastfm_energy_and_google_tasks_positive'
        elif correlation < -0.5:
            return 'lastfm_energy_and_google_tasks_negative'
        else:
            return 'lastfm_energy_and_google_tasks_neutral'

'''
class LastFmScrobblesAndGoogleTasks(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'google_tasks': ('completed_task', Count),
                 'lastfm': ('scrobble', Count)}
                 
    def get_template_key(self, correlation):
        if correlation > 0.5:
            return 'lastfm_scrobbles_and_google_tasks_positive'
        elif correlation < -0.5:
            return 'lastfm_scrobbles_and_google_tasks_negative'
        else:
            return 'lastfm_scrobbles_and_google_tasks_neutral'
'''
