DATABASES = {
    'default': 'platform',
    'async': 'platform_async'
}

FITBIT_KEY = '9ccbbd64e65a4f5cbd6d69c90da5b2df'
FITBIT_SECRET = 'e1f72277b86c4ec9ae306fcbcfbb6642'
TWITTER_KEY = 'Qdu02XEsVCIEv15vQCnsQ'
TWITTER_SECRET = 'iqW9WdjLc8qSyChI70MYP25IMpuumc67UipmPkoktP0'
APP_SECRET_KEY = '3VqZOXR2p3tXZ3chNZFP2hWRsBBY53lChDlp8nApl90bCdbFPIkZ5iPnel4ECQi'
FOURSQUARE_CLIENT_ID = 'NXYGN5GRJN4QEL1TZ3RMWQGXQUWD4JOKIEZ2U4NMGOSKX4NV'
FOURSQUARE_CLIENT_SECRET = 'QFPG1TE2HX2VJYAW14HXBDR0GDBVL3O231UVPQEWMSQAPP10'
LASTFM_KEY = '3b3e0d661f59cf22325db85784bd25ed'
LASTFM_SECRET = '72c62e1b9d0ac4bb7c3a56836f4cf885'
GOOGLE_KEY = '825237488185.apps.googleusercontent.com'
GOOGLE_SECRET = 'FH_tIvjgavOjl96wPU67Agn_'
ECHO_NEST_KEY = 'IBK1KKUMNX8MB7UHR'
ECHO_NEST_ID_LIMIT = 10

HOST = "localhost"
PORT = 5000
DEBUG = True 

# Override any of the above settings if they are specified in settings_local.py
from settings_local import *
