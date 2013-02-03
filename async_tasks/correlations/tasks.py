import logging
import numpy
from correlations.correlationfinder import CorrelationFinder
from correlations.constants import MINIMUM_DATAPOINTS_FOR_CORRELATION
from ..models import Correlation, Count, Average
from collections import OrderedDict

# By default numpy just raises warnings when it encounters problems.
# I want it to raise exceptions so I can catch and log them.
numpy.seterr(all='raise')

class CorrelationTask(object):
    def __init__(self, user, available_datastreams,
    window_size = MINIMUM_DATAPOINTS_FOR_CORRELATION, logger = None,
    use_cache = True):
        self.user = user
        self.available_datastreams = set(available_datastreams)
        self.window_size = window_size
        self.correlations = []
        self.use_cache = use_cache
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
            finder = CorrelationFinder(self.user, self.required_aspects,
                window_size = self.window_size, thresholds = self.thresholds,
                use_cache = self.use_cache)
            self.correlations = finder.get_correlations()
        
class LastFmEnergyAndGoogleTasks(CorrelationTask):

    @property
    def required_aspects(self):
        return {'google_tasks': [('completed_task', Count)],
                 'lastfm': [('song_energy', Average)]}
           
    @property
    def thresholds(self):
        return ['> 0.5', '< -0.5']


class LastFmScrobblesAndGoogleTasks(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'google_tasks': [('completed_task' , Count)],
                 'lastfm': [('scrobble', Count)]}
                 
    @property
    def thresholds(self):
        return ['> 0.5', '< -0.5']


class LastFmScrobblesAndLastFmEnergy(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'lastfm': [('song_energy', Average), ('scrobble', Count)]}

    @property
    def thresholds(self):
        return ['> 0.5', '< -0.5']
