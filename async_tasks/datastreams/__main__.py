## For testing purposes.
## Does *almost* the same thing as runner.py, but uses mock API objects instead
## and runs synchronously instead of asynchronously through Celery.

import runner
from auth.mocks import APIS

runner.run_tasks(APIS)
