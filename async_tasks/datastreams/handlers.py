import datetime
import logging
from pyechonest import song as pyechonest_song
from pyechonest.util import EchoNestAPIError

from api.constants import INTERVALS
from settings import ECHO_NEST_ID_LIMIT
from email.utils import parsedate_tz
from ..models import Count, Average, HourCount
from oauth_provider.models import User

class TimeSeriesHandler(object):
    def __init__(self, datastream_name, user, logger = None):
        self.user = user
        self.datastream_name = datastream_name
        self.logger = logger if logger else logging.getLogger(__name__)
    
    def get_timeslots(self, datetime_obj, intervals = INTERVALS):
        slots = {
            #'hour': Count.get_hour(datetime_obj),
            'day': Count.get_day_start(datetime_obj),
            'week': Count.get_week_start(datetime_obj),
            'month': Count.get_month_start(datetime_obj),
            'year': Count.get_year_start(datetime_obj)
        }
        
        for key in slots.keys():
            if key not in intervals:
                del slots[key]
                
        return slots
        
    def get_interval_key(self, interval, start):
        return '%s:%s' % (interval, start)

class PostCounter(TimeSeriesHandler):
    aspect = 'post'
    
    def __init__(self, *args, **kwargs):
        self.counts = {}
        super(PostCounter, self).__init__(*args, **kwargs)
        
    def handle(self, post, intervals = INTERVALS):
        date_posted = self.get_datetime(post)
        slots = self.get_timeslots(date_posted, intervals = intervals)
        
        for interval, start in slots.items():
            count_key = self.get_interval_key(interval, str(start))
            
            if count_key not in self.counts:
                self.counts[count_key] = Count.find_or_create(
                    user_id = self.user['_id'],
                    interval = interval,
                    start = slots[interval],
                    datastream = self.datastream_name,
                    aspect = self.aspect
                )
            
            self.counts[count_key].count += 1

    def finalize(self):
        for count in self.counts:
            self.counts[count].save()
            
class PostHourCounter(PostCounter):
    def get_interval_key(self, interval, start, posted):
        return '%s:%s:%s' % (interval, start, posted.hour)
    
    def handle(self, post, intervals = INTERVALS):
        date_posted = self.get_datetime(post)
        slots = self.get_timeslots(date_posted, intervals = intervals)
        
        for interval, start in slots.items():
            count_key = self.get_interval_key(interval, str(start), date_posted)
            
            if count_key not in self.counts:
                self.counts[count_key] = HourCount.find_or_create(
                    user_id = self.user['_id'],
                    interval = interval,
                    start = slots[interval],
                    datastream = self.datastream_name,
                    aspect = self.aspect,
                    hour = date_posted.hour
                )
            
            self.counts[count_key].count += 1

class TwitterPostMixin(object):
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
        dt = datetime.datetime(*time_tuple[:6])
        return dt - datetime.timedelta(seconds=time_tuple[-1])

class TwitterPostCounter(PostCounter, TwitterPostMixin):
    aspect = "tweet"
    
    def __init__(self, user):
        super(TwitterPostCounter, self).__init__('twitter', user)
        

class TwitterPostHourCounter(PostHourCounter, TwitterPostMixin):
    aspect = "tweet"
    
    def __init__(self, user):
        super(TwitterPostHourCounter, self).__init__('twitter', user)


class LastfmScrobbleMixin(object):
    def get_datetime(self, post):
        assert 'date' in post
        assert 'uts' in post['date']
        time_tuple = datetime.datetime.utcfromtimestamp(
            int(post['date']['uts'].strip())).timetuple()
        dt = datetime.datetime(*time_tuple[:6])
        return dt - datetime.timedelta(seconds=time_tuple[-1])

class LastfmScrobbleCounter(LastfmScrobbleMixin, PostCounter):
    aspect = 'scrobble'
    
    def __init__(self, user):
        super(LastfmScrobbleCounter, self).__init__('lastfm', user)
        
class LastfmScrobbleHourCounter(LastfmScrobbleMixin, PostHourCounter):
    aspect = 'scrobble'
    
    def __init__(self, user):
        super(LastfmScrobbleHourCounter, self).__init__('lastfm', user)

class GoogleCompletedTasksCounter(PostCounter):
    aspect = "completed_task"
    
    def __init__(self, user):
        super(GoogleCompletedTasksCounter, self).__init__('google_tasks', user)
        
    def get_datetime(self, post):
        assert 'completed' in post
        return datetime.datetime.strptime(
            post['completed'].strip()[0:10], '%Y-%m-%d')


class LastfmSongEnergyAverager(LastfmScrobbleMixin, TimeSeriesHandler):
    aspect = 'song_energy'
    
    def __init__(self, user):
        super(LastfmSongEnergyAverager, self).__init__('lastfm', user)
        self.song_ids = []
        self.scrobbles = []
        
    def handle(self, scrobble, intervals = INTERVALS):
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
        energy = {}
        averages = {}
        
        songs = self.get_songs(self.song_ids)
        
        # Index energy levels by song and artist for lookup efficiency later.
        for song in songs:
            artist = song.artist_name
            if artist not in energy:
                energy[artist] = {}
                
            energy[artist][song.title] = song.audio_summary['energy']
            
        # Go through the scrobbles we summarized earlier and create Average
        # objects with the total energy for the interval as the numerator and
        #  the total number of songs for the interval as the denominator.
        for scrobble in self.scrobbles:
            slots = self.get_timeslots(scrobble['datetime'])
            
            for interval, start in slots.items():
                interval_key = self.get_interval_key(interval, start)
                if interval_key not in averages:
                    
                    # We might be able to make this more efficient if we can
                    # be assured that users will never scrobble retroactively
                    # and that we only average on *complete* time periods.
                    # (E.g., no creating an Average for the month we're in.)
                    averages[interval_key] = Average.find_or_create(
                        user_id = self.user['_id'],
                        datastream = self.datastream_name,
                        aspect = self.aspect,
                        interval = interval,
                        start = start)
                
                # Unfortunately Echo Nest doesn't know about all the songs a
                # user may scrobble.
                if (scrobble['artist'] in energy
                and scrobble['track'] in energy[scrobble['artist']]):
                    averages[interval_key].numerator += (
                        energy[scrobble['artist']][scrobble['track']])
                    averages[interval_key].denominator += 1
                
        # Save all the Average objects.
        for average in averages.values():
            average.save()
