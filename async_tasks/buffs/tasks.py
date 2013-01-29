from api import INTERVALS
from async_tasks.models import Count, Average
from collections import OrderedDict

class CorrelationTask(object):
    def __init__(self, user, available_datastreams):
        self.user = user
        self.available_datastreams = set(available_datastreams)
        
    @property
    def required_aspects(self):
        raise NotImplemented("Inheriting classes must implement this.")
        
    def get_template_key(self, aspects):
        raise NotImplemented("Inheriting classes must implement this.")
        
    def run(self):
        # Create a dictionary of interval keys to dictionaries of
        # datastream keys to empty dictionaries.
        data = dict([(interval, []) for interval in INTERVALS])
        
        # Do we have the required datastreams to run this correlation?
        if set(self.required_aspects).issubset(self.available_datastreams):
            
            # Get the data corresponding to every aspect required.
            for (datastream, (aspect, aspect_class)
            in self.required_aspects.items()):
                
                # And get the data for that aspect for every interval.
                # TODO: Limit this query. It'll get huge pretty quickly.
                # Also, it kinda bothers me that we have a query in a nested
                # 'for' loop! Seems *super* inefficient.
                for interval in INTERVALS:
                    data[interval].append((OrderedDict(
                        [(row['interval_start'], aspect_class.get_data(row))
                            for row in aspect_class.get_collection().find(
                            {'user_id': self.user['_id'],
                             'datastream': datastream,
                             'aspect': aspect,
                             'interval': interval
                            }).sort({'interval_start': -1})
                    ]))
        
        # Okay, now let's look for some correlations!
        for buff in self.create_buffs(data):
            buff.save()
        
    def create_buffs(data):
        for interval, datapoints in data.keys():
            # Right now we're just assuming that there is no data available
            # for a datapoint if there is no entry for it.
            # TODO: Make missing datapoints imply 0 for continuous datastream
            # aspects like Twitter and Last.fm counts.
            raise NotImplemented()
                
        
class LastFmEnergyAndGoogleTasks(CorrelationTask):
    
    @property
    def required_aspects(self):
        return {'google_tasks': ('completed_task', Count),
                 'lastfm': ('song_energy', Average)}
                 
    
