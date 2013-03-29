''''
Provides environment switching for settings via command line parameters.
Specifically, it allows the user to specify whether to use the "test" settings,
which comes in handy when starting up the server for the sake of running
automated tests against it.
'''
import app
import argparse
import glob
import bson.json_util
import nose
import pymongo
import settings
import settings_test
import sys

def get_args():
    parser = argparse.ArgumentParser(description='Run the web app.')
    parser.add_argument('--test', dest='env_settings', action='store_const',
        const = settings_test, default = settings,
        help=('use the settings in settings_test'))
    parser.add_argument('--unittests', dest='run_unittests',
        action='store_const', const = True, default = False,
        help='run unit tests')
    parser.add_argument('--apitests', dest='run_apitests',
        action='store_const', const = True, default = False,
        help='run tests against the API server')
    parser.add_argument('--no-server', dest='run_server',
        action='store_const', const = False, default = True,
        help='do not start the server')
    parser.add_argument('--reset-db', dest='reset_db',
        action='store_const', const = True, default = False,
        help='wipe out the database and restore from fixtures')
    parser.add_argument('--use-reloader', dest='use_reloader',
        action='store_const', const = True, default = False,
        help='reload server on file change (do not use with --reset-db)')
    parser.add_argument('--fixtures', action='store', dest='fixtures_path',
        type=str, default='fixtures', help='directory to load fixtures from')
    return parser.parse_args()

def main(args):
    settings = args.env_settings
    
    if args.reset_db:
        if args.use_reloader:
            print "--use-reloader set. Ignoring --reset-database."
        else:
            really_reset = raw_input(
                ("Resetting the databases (%s) " % ', '.join(
                    settings.DATABASES.values()))
                + " will permanently delete all the data in them!\nAre you sure "
                + "you want to do this? (Y/N)")
            
            if really_reset.upper() == "Y":
                print "\nWiping dbs and loading fixtures..."
               
                # Using keys() instead of values() because we want to
                # load the same fixtures whether or not we're testing.
                for db_key, db_name in settings.DATABASES.items():
                    pymongo.MongoClient().drop_database(db_name)
                    db = pymongo.MongoClient()[db_name]
                
                    # Go through every JSON file in the fixtures directory and
                    # insert the objects in the JSON files into collections named
                    # after the JSON files they came from.
                    for f in glob.iglob("%s/%s/*.json" % (
                    args.fixtures_path, db_key)):
                        print "Loading " + f
                    
                        with open(f, 'r') as fixture:
                            for rows in bson.json_util.loads(fixture.read()):
                                db[f.split('/')[-1].split('.')[0]].insert(rows)
                
                print "Fixtures successfully loaded!\n"
                
            else:
                print "Ignoring --reset-database this time, then."
           
    if args.run_unittests:
        nose.run(argv = sys.argv[:1])
        
    if args.run_apitests:
        nose.run(argv = ['nosetests', '-a', 'api_test', 'api/functional_tests.py'])
        
    if args.run_server:
        app.main(settings = settings, use_reloader = args.use_reloader)

if __name__ == '__main__':
    main(get_args())
