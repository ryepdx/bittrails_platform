import pymongo
import logging
import settings
import datetime, time, pytz
from ..models import TimeSeriesData

def main():
    one_hour = datetime.timedelta(hours = 1)
    now = datetime.datetime.now(pytz.utc)
    last_one = TimeSeriesData.find({"parent_path":None}
        ).sort("_id", pymongo.DESCENDING).limit(1)
    
    if last_one.count() > 0:
        timestamp = last_one[0]['timestamp'].replace(tzinfo=pytz.utc) + one_hour
    else:
        if settings.DEBUG:
            timestamp = datetime.datetime(2010, 1, 1, tzinfo=pytz.utc)
        else:
            timestamp = datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
        
    logging.info("Starting from " + timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        
    while timestamp < now:
        isocalendar = timestamp.isocalendar()
        TimeSeriesData.get_collection().insert(
            {   "year": timestamp.year,
                "month": timestamp.month,
                "week": int(timestamp.strftime("%W")),
                "day": timestamp.day,
                "isoyear": isocalendar[0],
                "isoweek": isocalendar[1],
                "isoweekday": isocalendar[2],
                "hour": timestamp.hour,
                "user_id" : None,
                "timestamp" : timestamp,
                "parent_path" : None,
                "name" : None,
                "value" : 0
            })
        
        timestamp += one_hour

retry = True
retry_attempts = 0
while retry:
    try:
        main()
        retry = False
    except Exception as err:
        retry_attempts += 1
        logging.error("Error: %s. Retrying in %s seconds. " % (err.message, retry_attempts))
        time.sleep(retry_attempts)
        retry = (retry_attempts < 10)
