import ast
import datetime
import iso8601
import logging
from pyechonest import song as pyechonest_song
from pyechonest.util import EchoNestAPIError

from settings import ECHO_NEST_ID_LIMIT
from email.utils import parsedate_tz
from ..models import TimeSeriesData, TimeSeriesPath, CustomTimeSeriesData
from oauth_provider.models import User


class CSVHandler(object):
    model_class = CustomTimeSeriesData
    
    def __init__(self, stream, logger = None):    
        self.stream = stream
        self.logger = logger if logger else logging.getLogger(__name__)
        
    def handle(self, row):
            datum = self.model_class.find_or_create(
                user_id = self.stream['user_id'],
                client_id = self.stream['client_id'],
                parent_path = (self.stream.get('parent_path', '')
                    + self.stream['name'] + "/"),
                timestamp = self.get_datetime(row)
            )
            datum.value = ast.literal_eval(row['value'])
            datum.save()
        
    def get_datetime(self, row):
        return iso8601.parse_date(row['date'])
        
    def finalize(self):
        pass
    

class TimeSeriesHandler(object):
    model_class = TimeSeriesData
    handler_classes = []
    
    def __init__(self, user, logger = None):    
        self.user = user
        self.logger = logger if logger else logging.getLogger(__name__)
        
        parent_path = ''
        path_parts = self.path.strip('/').split('/')
        
        # Is there a path to this handler's data in the database?
        # Create one if not.
        path_parts_length = len(path_parts)
        if path_parts_length > 1:
            for i in range(0, path_parts_length):
                custom_path = TimeSeriesPath.find_or_create(
                    user_id = user['_id'], parent_path = parent_path,
                    name = path_parts[i]).save()
                
                parent_path = parent_path + '/'.join(path_parts[0:i+1]) + '/'
        
    
    def get_accumulator_key(self, timestamp):
        return timestamp.strftime('%Y-%m-%d %H')


class TotalHandler(TimeSeriesHandler):
    path = 'posts'
    
    def __init__(self, *args, **kwargs):
        self.totals = {}
        super(TotalHandler, self).__init__(*args, **kwargs)
        
    def handle(self, post):
        timestamp = self.get_datetime(post)
        total_key = self.get_accumulator_key(timestamp)
        
        if total_key not in self.totals:
            self.totals[total_key] = self.model_class.find_or_create(
                user_id = self.user['_id'],
                parent_path = self.path + "/",
                timestamp = timestamp
            )
            
        self.totals[total_key].value += 1

    def finalize(self):
        for total in self.totals.values():
            total.save()
    
    
class TwitterTweet(TotalHandler):
    path = 'twitter/tweets'
    
    def get_datetime(self, post):
        try:
            assert 'created_at' in post
        except AssertionError as err:
            self.logger.critical(
                'While getting tweets for user %s on tweet: %s'
                    % (self.user['_id'], str(post)),
                exc_info = err)
            raise
        time_tuple = parsedate_tz(post['created_at'].strip())
        return datetime.datetime(*time_tuple[:6])
    
    
class GoogleCompletedTask(TotalHandler):
    path = 'google/tasks/completed'
    
    def get_datetime(self, post):
        assert 'completed' in post
        return iso8601.parse_date(post['completed'])
    
    
class LastfmScrobble(TotalHandler):
    path = 'lastfm/scrobbles'
    
    def get_datetime(self, post):
        assert 'date' in post
        assert 'uts' in post['date']
        time_tuple = datetime.datetime.utcfromtimestamp(
            int(post['date']['uts'].strip())).timetuple()
        return datetime.datetime(*time_tuple[:6])
        
    
class LastfmScrobbleEchonest(LastfmScrobble):
    path = LastfmScrobble.path + '/echonest' 
    
    def __init__(self, *args, **kwargs):
        super(LastfmScrobbleEchonest, self).__init__(*args, **kwargs)
        self.song_ids = []
        self.scrobbles = []
        
    def handle(self, scrobble):
        # Last.fm returns the MusicBrainz ID of each song you scrobble.
        if 'mbid' in scrobble and scrobble['mbid']:
            # Echo Nest can use the MusicBrainz ID to look up the audio summary.
            # We're not looking it up now, though, since we can pass multiple
            # IDs in a single request. It's much more efficient to do it that
            # way, at least as far as number of requests to Echo Nest goes.
            self.song_ids.append('musicbrainz:song:' + scrobble['mbid'])
            
            # Keeping track of artist and track names so we can match scrobble
            # times with the audio summaries returned by Echo Nest later.
            self.scrobbles.append({
                'artist': scrobble['artist']['#text'],
                'track': scrobble['name'],
                'datetime': self.get_datetime(scrobble)
            })
            
    def get_songs(self, song_ids):
        songs = []
        
        # Echo Nest limits the number of IDs you can include in a single request.
        id_chunks = [song_ids[i*ECHO_NEST_ID_LIMIT:(i + 1) * ECHO_NEST_ID_LIMIT]
            for i in range(0, (len(self.song_ids) / ECHO_NEST_ID_LIMIT) + 1)]
            
        # Using a while loop because we want it to reevaluate the conditional
        # expression every time through the loop.
        i = 0        
        chunks_len = len(id_chunks)
        
        while i < chunks_len:
            try:
                songs += pyechonest_song.profile(id_chunks[i],
                    buckets = ['audio_summary'])
                i += 1
            except EchoNestAPIError:
                if isinstance(id_chunks[i], list) and len(id_chunks[i]) > 1:
                    mid = len(id_chunks[i]) / 2
                    
                    # Split the current ID chunk if it's not composed of 1 id.
                    # Otherwise just skip it.
                    id_chunks = (
                        id_chunks[:i]
                        + [id_chunks[i][:mid]]
                        + [id_chunks[i][mid:]]
                        + id_chunks[i+1:]
                    )
                    # Update the chunks count.
                    chunks_len = len(id_chunks)
                else:
                    i += 1
            
        return songs
            
    def finalize(self):
        energy_lookup = {}
        energy_objs = {}
        
        songs = self.get_songs(self.song_ids)
        
        # Index energy levels by song and artist for lookup efficiency later.
        for song in songs:
            artist = song.artist_name
            if artist not in energy_lookup:
                energy_lookup[artist] = {}
                
            energy_lookup[artist][song.title] = song.audio_summary['energy']
            
        # Go through the scrobbles we summarized earlier and create objects
        # containing the totals for all the song energies we looked up.
        for scrobble in self.scrobbles:
            energy_key = self.get_accumulator_key(scrobble['datetime'])
            
            if energy_key not in energy_objs:
                energy_objs[energy_key] = {
                    'energy/totals':
                        self.model_class.find_or_create(
                        user_id = self.user['_id'],
                        parent_path = self.path + "/energy/",
                        timestamp = scrobble['datetime']),
                    'totals':
                        self.model_class.find_or_create(
                        user_id = self.user['_id'],
                        parent_path = self.path + "/",
                        timestamp = scrobble['datetime'])
                }
            
            # Unfortunately Echo Nest doesn't know about all the songs a
            # user may scrobble. Make sure we have the energy for the song
            # before we go trying to add it to our numerator.
            if (scrobble['artist'] in energy_lookup
            and scrobble['track'] in energy_lookup[scrobble['artist']]):
                energy_objs[energy_key]['energy/totals'].value += (
                    energy_lookup[scrobble['artist']][scrobble['track']])
                energy_objs[energy_key]['totals'].value += 1
                
        # Save all the totals.
        for energy_obj in energy_objs.values():
            energy_obj['energy/totals'].save()
            energy_obj['totals'].save()
