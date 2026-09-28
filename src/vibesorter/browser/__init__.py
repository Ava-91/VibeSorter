"""Local visual browser for cached VibeSorter analysis."""


from . import query_compat as _query_compat
from . import server as _server

_query_compat.install(_server)
