# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|

"""Server-layer exceptions that span task_manager and request handlers.

Lives in its own module so handlers and the manager can both import from it
without creating an import cycle.
"""

from __future__ import annotations


class MalformedContextIdError(ValueError):
    """Raised when a client supplies a context_id that is not a valid UUID.

    Why: silently generating a fresh UUID for malformed input would orphan
    the caller's intended context and let an attacker amplify storage by
    sending unbounded distinct garbage values. Handlers turn this into a
    JSON-RPC -32602 ("Invalid params") response so the client can fix it.
    """
