import logging
import numpy
import utils
from api import INTERVALS
import async_tasks.models
from .settings import MINIMUM_DATAPOINTS_FOR_CORRELATION
from ..models import Correlation
from collections import OrderedDict

# By default numpy just raises warnings when it encounters problems.
# I want it to raise exceptions so I can catch and log them.
numpy.seterr(all='raise')

class CorrelationTask(object):
    def __init__(self, user, available_datastreams,
    window_size = MINIMUM_DATAPOINTS_FOR_CORRELATION, logger = None):
        self.user = user
        self.available_datastreams = set(available_datastreams)
        self.window_size = window_size
        self._logger = logger if logger else logging
        
    @property
    def required_aspects(self):
        raise NotImplemented("Inheriting classes must implement this.")
        
    def get_template_key(self, correlation):
        raise NotImplemented("Inheriting classes must implement this.")
        
    def run(self):
        # Do we have the required datastreams to run this correlation?
        if set(self.required_aspects).issubset(self.available_datastreams):
            
            # Okay, now let's look for some correlations!
            self.save_correlations(utils.find_correlations(self.user,
                utils.get_matrix_for_correlation(
                    self.user, self.required_aspects),
                thresholds = self.thresholds))
                    
    # Broke this out into its own function so we can override it for testing.
    def save_correlations(self, correlations):
        for correlation in correlations:
            Correlation(
                user_id = self.user['_id'],
                key = Correlation.generate_key(self.required_aspects),
                window_size = self.window_size,
                **correlation[1]
            ).save()
        
        
class LastFmEnergyAndGoogleTasks(CorrelationTask):

    @property
    def required_aspects(self):
        return {'google_tasks': ['completed_task_count'],
                 'lastfm': ['song_energy_average']}
           
    @property
    def thresholds(self):
        return ['> 0.5', '< -0.5']


class LastFmScrobblesAndGoogleTasks(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'google_tasks': ['completed_task_count'],
                 'lastfm': ['scrobble_count']}
                 
    @property
    def thresholds(self):
        return ['> 0.5', '< -0.5']


class LastFmScrobblesAndLastFmEnergy(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'lastfm': ['song_energy_average', 'scrobble_count']}

    @property
    def thresholds(self):
        return ['> 0.5', '< -0.5']
