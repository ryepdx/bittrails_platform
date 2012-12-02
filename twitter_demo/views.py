from flask import Blueprint, session, request
from datetime import datetime

TWITTER_REQUEST = "https://api.twitter.com/1.1/statuses/user_timeline.json"
app = Blueprint('twitter_demo', __name__)

@app.route('/')
def twitter_demo():
    if 'twitter_user' in session:
        user = session['twitter_user']
        if 'user' in request.args:
            user = request.args['user']
        count = 300
        if 'count' in request.args:
            try:
                count = int(request.args['count'])
            finally:
                pass
        #user = "LucianNovo"
        session['user'] = user
        userdata, tweets = get_tweet_data(user, count)
        utc_offset = userdata['utc_offset']
        average_day = calculate_per_day(tweets, utc_offset)
        session['tweets'] = tweets
        session['average_per_day'] = average_day
        clean_test_values()
        #session['test_value'] = 
        #session['test_dict'] = average_day
        session['test_dict'] = average_day
        #session['test_list_value_key'] = 
        return render_template('print.html')
        
    return render_template('twitter.html')

def convert_twitter_time(time_string):
    a = re.search("\+[0-9]{4} ", time_string)
    time_string = time_string[:a.start()]+time_string[a.end():].strip()
    time = datetime.strptime(time_string, "%a %b %d %H:%M:%S %Y")
    return time.strftime("%Y-%m-%d %H:%M:%S")

def twitter_time_str_to_datetime(time_string):
    a = re.search("\+[0-9]{4} ", time_string)
    time_string = time_string[:a.start()]+time_string[a.end():].strip()
    return datetime.strptime(time_string, "%a %b %d %H:%M:%S %Y")

def format_datetime(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def suffix(i):
    if i < 12: return 'am'
    else: return 'pm'

def hour_str(i):
    return str((i-1)%12+1)+suffix(i)

def get_tweet_data(user, count):
    DATA_TO_KEEP = {'id' : 'id',
                    'timestamp' : 'created_at',
                    'text' : 'text'}
    tweets = list()
    userdata = None
    while (count > 0):
        #keep track of how many tweets to get
        get = 30
        if (count < 30):
            get = count
        count -= get
        data = {"screen_name" : user,
                "count" : str(get)}
        if len(tweets): #don't get the same tweets twice
            data["max_id"] = str(tweets[-1]['id']-1)
        resp = twitter.get(TWITTER_REQUEST,
                           data = data,
                           token = session.get('twitter_token'))
        if not userdata:
            userdata = resp.data[0]['user']
        for tweet_data in resp.data:
            tweet_slim = dict()
            for key in DATA_TO_KEEP:
                tweet_slim[key] = tweet_data[DATA_TO_KEEP[key]]
            tweets.append(tweet_slim)
    return userdata, tweets

def calculate_per_day(tweets, offset):
    latest = twitter_time_str_to_datetime(tweets[0]['timestamp'])
    earliest = twitter_time_str_to_datetime(tweets[-1]['timestamp'])
    num_days = (latest-earliest).days
    if num_days == 0: num_days = 1
    day = dict()
    for i in range(24):
        day[i] = 0
    for tweet in tweets:
        dt = twitter_time_str_to_datetime(tweet['timestamp'])
        dt += timedelta(seconds = offset)
        day[dt.hour] += 1
    return OrderedDict([(hour_str(hour), 1.0*day[hour]) for hour in range(24)])
##    return [hour_str(i) for i in range(24)], \
##           [1.0*day[hour]/num_days for hour in day.keys()]

def clean_test_values():
    if 'test_value' in session: del session['test_value']
    if 'test_dict' in session: del session['test_dict']
    if 'test_list' in session: del session['test_list']
    if 'test_list_value_key' in session: del session['test_list_value_key']
