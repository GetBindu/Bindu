# shared/config.py

import os

USE_FAKE_DATA = os.getenv("USE_FAKE_DATA", "true").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 5))