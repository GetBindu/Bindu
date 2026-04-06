# shared/config.py

import os

USE_FAKE_DATA = os.getenv("USE_FAKE_DATA", "true").lower() == "true"
REBALANCE_FRACTION = float(os.getenv("REBALANCE_FRACTION"))
try:
    REQUEST_TIMEOUT = max(1, int(os.getenv("REQUEST_TIMEOUT", 5)))
except ValueError:
    REQUEST_TIMEOUT=5