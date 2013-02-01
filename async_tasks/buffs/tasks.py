import logging
import numpy
from api import INTERVALS
import async_tasks.models
from ..models import Correlation
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
            for datastream in self.required_aspects:
                for aspect_string in self.required_aspects[datastream]:
                    aspect, aspect_class = aspect_string.rsplit('_', 1)
                    aspect_class = getattr(
                        async_tasks.models, aspect_class.title())
                    data_history = dict(
                        [(interval, OrderedDict()) for interval in INTERVALS]) 
                    
                    # And get the data for that aspect for every interval.
                    datapoints = aspect_class.get_collection().find(
                        {'user_id': self.user['_id'], 'datastream': datastream,
                         'aspect': aspect}).sort('interval_start', -1)
                         
                    # Cycle through the datapoints and separate them by interval
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
            if len(interval_keys) >= MINIMUM_DATAPOINTS_FOR_CORRELATION:
                datapoints_list = [OrderedDict() for i in range(
                    0, len(datastream_list))]
                correlation = 0
                buff_template = None
                covered_interval_keys = []
                
                for key in interval_keys: # Cycle through all common dates.
                    for i, datastream in enumerate(datastream_list):
                        datapoints_list[i][key] = datastream[key]
                    
                    # Make sure there are enough datapoints in our sliding
                    # window to find a correlation.
                    if len(datapoints_list[0]
                    ) >= MINIMUM_DATAPOINTS_FOR_CORRELATION:
                        last_correlation = correlation
                        correlation = self.correlate(
                            [datapoint.values(
                            ) for datapoint in datapoints_list])
                        template_key = self.get_template_key(correlation)
                        
                        # Didn't find a correlation and we're not carrying
                        # forward a correlation?
                        if not template_key and not buff_template:
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
                        elif template_key != buff_template:
                            if buff_template:
                                buffs.append(
                                    self.create_buff(interval, 
                                    datapoints_list[0].keys()[0],
                                    datapoints_list[0].keys()[-2],
                                    last_correlation, buff_template)
                                )
                                
                                datapoints_list = [
                                    OrderedDict(datapoints_list[i].items()[-1:]
                                    ) for i in range(0, len(datapoints_list))]                                             
                                
                            # Either way, update buff_template.
                            buff_template = template_key
                
                # If a template key was found, then there was a significant
                # correlation found. Create a buff.
                if buff_template:
                    buffs.append(self.create_buff(
                        interval, datapoints_list[0].keys()[0],
                        interval_keys[-1], correlation, buff_template))
                    
        return buffs
        
        
    def create_buff(self, interval, start, end, correlation, template_key):
        return Correlation(
            user_id = self.user['_id'],
            interval = interval,
            interval_start = start,
            interval_end = end, 
            correlation = correlation,
            key = Correlation.generate_key(self.required_aspects)
        )
        
    def correlate(self, matrix):
        # Return the correlation strength between the two variables.
        # This number will be found in the lower left-hand corner of the
        # returned correlation matrix.
        try:
            return numpy.corrcoef(matrix)[-1][0]
        except FloatingPointError as err:
            self._logger.error(
                ("Floating point error while finding correlations " 
                + "for user %s." % self.user['_id']), exc_info = err)
            return 1
        except Exception as err:
            self._logger.error(("Error while finding correlations " 
                + "for user %s." % self.user['_id']), exc_info = err)
        
        
class LastFmEnergyAndGoogleTasks(CorrelationTask):

    @property
    def required_aspects(self):
        return {'google_tasks': ['completed_task_count'],
                 'lastfm': ['song_energy_average']}
                 
    def get_template_key(self, correlation):
        if correlation > 0.5:
            return 'lastfm_energy_and_google_tasks_positive'
        elif correlation < -0.5:
            return 'lastfm_energy_and_google_tasks_negative'
        else:
            #return 'lastfm_energy_and_google_tasks_neutral'
            return None


class LastFmScrobblesAndGoogleTasks(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'google_tasks': ['completed_task_count'],
                 'lastfm': ['scrobble_count']}
                 
    def get_template_key(self, correlation):
        if correlation > 0.5:
            return 'lastfm_scrobbles_and_google_tasks_positive'
        elif correlation < -0.5:
            return 'lastfm_scrobbles_and_google_tasks_negative'
        else:
            return None


class LastFmScrobblesAndLastFmEnergy(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'lastfm': ['song_energy_average', 'scrobble_count']}
                 
    def get_template_key(self, correlation):
        if correlation > 0.5:
            return 'lastfm_scrobbles_and_lastfm_energy_positive'
        elif correlation < -0.5:
            return 'lastfm_scrobbles_and_lastfm_energy_negative'
        else:
            return None
