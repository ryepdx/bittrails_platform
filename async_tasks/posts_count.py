import datetime
from pyechonest import song as pyechonest_song

from api import INTERVALS
from email.utils import parsedate_tz
from models import PostsCount, Average
from oauth_provider.models import User

class TimeSeriesHandler(object):
    def __init__(self, datastream_name, user):
        self.user = user
        self.datastream_name = datastream_name
    
    def get_timeslots(self, datetime_obj, intervals = INTERVALS):
        slots = {
            #'hour': self.get_hour(datetime_obj),
            'day': PostsCount.get_day_start(datetime_obj),
            'week': PostsCount.get_week_start(datetime_obj),
            'month': PostsCount.get_month_start(datetime_obj),
            'year': PostsCount.get_year_start(datetime_obj)
        }
        
        for key in slots.keys():
            if key not in intervals:
                del slots[key]
                
        return slots
        
    def get_interval_key(self, interval, interval_start):
        return '%s:%s' % (interval, interval_start)

class PostCounter(TimeSeriesHandler):
    def __init__(self, *args, **kwargs):
        self.counts = {}
        super(PostCounter, self).__init__(*args, **kwargs)
        
    def handle(self, post, intervals = INTERVALS):
        date_posted = self.get_datetime(post)
        slots = self.get_timeslots(date_posted, intervals = intervals)
        
        for interval, interval_start in slots.items():
            interval_key = self.get_interval_key(interval, str(interval_start))
            
            if count_key not in self.counts:
                self.counts[count_key] = PostsCount.find_or_create(
                    user_id = self.user['_id'],
                    interval = interval,
                    interval_start = slots[interval],
                    datastream = self.datastream_name
                )
            
            self.counts[count_key].posts_count += 1

    def finalize(self):
        for count in self.counts:
            self.counts[count].save()


class TwitterPostCounter(PostCounter):
    def __init__(self, user):
        super(TwitterPostCounter, self).__init__('twitter', user)
        
    @classmethod
    def get_datetime(cls, post):
        assert 'created_at' in post
        time_tuple = parsedate_tz(post['created_at'].strip())
        dt = datetime.datetime(*time_tuple[:6])
        return dt - datetime.timedelta(seconds=time_tuple[-1])

class LastfmScrobbleCounter(PostCounter):
    def __init__(self, user):
        super(LastfmScrobbleCounter, self).__init__('lastfm', user)
        
    @classmethod
    def get_datetime(cls, post):
        assert 'date' in post
        assert 'uts' in post['date']
        time_tuple = datetime.datetime.utcfromtimestamp(
            int(post['date']['uts'].strip())).timetuple()
        dt = datetime.datetime(*time_tuple[:6])
        return dt - datetime.timedelta(seconds=time_tuple[-1])

class GoogleCompletedTasksCounter(PostCounter):
    def __init__(self, user):
        super(GoogleCompletedTasksCounter, self).__init__('google_tasks', user)
        
    @classmethod
    def get_datetime(cls, post):
        assert 'completed' in post
        return datetime.datetime.strptime(
            post['completed'].strip()[0:10], '%Y-%m-%d')


class LastfmSongEnergyAverager(TimeSeriesHandler):
    def __init__(self, user):
        super(LastfmSongEnergyAverager, self).__init__('lastfm', user)
        self.song_ids = []
        self.scrobbles = []
        
    def handle(self, scrobble, intervals = INTERVALS):
        # Last.fm returns the MusicBrainz ID of each song you scrobble.
        if 'mbid' in scrobble:
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
                'datetime': LastfmScrobbleCounter.get_datetime(scrobble)
            })
            
            
    def finalize(self):
        energy = {}
        averages = {}
        songs = pyechonest_song.profile(
            ids = self.song_ids, buckets = ['audio_summary'])
        
        # Index energy levels by song and artist for lookup efficiency later.
        for song in songs['response']['songs']:
            artist = song['artist_name']
            if artist not in energy:
                energy[artist] = {}
                
            energy[artist][song['title']] = song['audio_summary']['energy']
            
        # Go through the scrobbles we summarized earlier and create Average
        # objects with the total energy for the interval as the numerator and
        #  the total number of songs for the interval as the denominator.
        for scrobble in self.scrobbles:
            slots = self.get_timeslots(scrobble['datetime'])
            
            for interval, interval_start in slots.items():
                interval_key = self.get_interval_key(interval, interval_start)
                if interval_key not in averages:
                    
                    # We might be able to make this more efficient if we can
                    # be assured that users will never scrobble retroactively
                    # and that we only average on *complete* time periods.
                    # (E.g., no creating an Average for the month we're in.)
                    averages[interval_key] = Average.find_or_create(
                        datastream = self.datastream_name,
                        interval = interval,
                        interval_start = which_interval)
                
                averages[interval_key].numerator += energy[scrobble['artist']][scrobble['track']]
                averages[interval_key].denominator += 1
                
        # Save all the Average objects.
        for average in averages.values():
            average.save()
