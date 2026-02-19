
import threading
import time
import os
import sys
import types
from unittest.mock import MagicMock, AsyncMock

# Add current directory to path so we can import 'bindu'
sys.path.insert(0, os.getcwd())

# --- Mocking External Dependencies ---

def mock_module(name):
    if name not in sys.modules:
        m = types.ModuleType(name)
        sys.modules[name] = m
    return sys.modules[name]

# Mock Starlette
starlette = mock_module("starlette")
starlette_requests = mock_module("starlette.requests")
starlette.requests = starlette_requests # Link to parent

starlette_responses = mock_module("starlette.responses")
starlette.responses = starlette_responses # Link to parent

starlette_middleware = mock_module("starlette.middleware")
starlette.middleware = starlette_middleware # Link to parent

starlette_middleware_base = mock_module("starlette.middleware.base")
starlette.middleware.base = starlette_middleware_base # Link to parent

starlette_applications = mock_module("starlette.applications")
starlette.applications = starlette_applications # Link to parent

class Starlette:
    def __init__(self, *args, **kwargs):
        self.state = MagicMock()
starlette_applications.Starlette = Starlette

class Middleware:
    def __init__(self, cls, **options):
        self.cls = cls
        self.options = options
starlette_middleware.Middleware = Middleware

class Route:
    pass
class Mount:
    pass
class WebSocketRoute:
    pass

# Add routing mocks if needed
starlette_routing = mock_module("starlette.routing")
starlette.routing = starlette_routing
starlette_routing.Route = Route
starlette_routing.Mount = Mount
starlette_routing.WebSocketRoute = WebSocketRoute

# Add other common starlette modules
starlette_types = mock_module("starlette.types")
starlette.types = starlette_types

starlette_datastructures = mock_module("starlette.datastructures")
starlette.datastructures = starlette_datastructures

starlette_status = mock_module("starlette.status")
starlette.status = starlette_status

starlette_exceptions = mock_module("starlette.exceptions")
starlette.exceptions = starlette_exceptions

starlette_concurrency = mock_module("starlette.concurrency")
starlette.concurrency = starlette_concurrency

starlette_background = mock_module("starlette.background")
starlette.background = starlette_background

# Mock HTTPException
class HTTPException(Exception):
    def __init__(self, status_code, detail=None):
        self.status_code = status_code
        self.detail = detail
starlette.exceptions.HTTPException = HTTPException

# Mock BackgroundTask
class BackgroundTask:
    def __init__(self, func, *args, **kwargs):
        pass
starlette.background.BackgroundTask = BackgroundTask

# Mock Websockets
starlette_websockets = mock_module("starlette.websockets")
starlette.websockets = starlette_websockets
class WebSocket:
    pass
starlette.websockets.WebSocket = WebSocket

# Mock Types
starlette_types = mock_module("starlette.types")
starlette.types = starlette_types
starlette.types.ASGIApp = types.ModuleType("ASGIApp")
starlette.types.Scope = types.ModuleType("Scope")
starlette.types.Receive = types.ModuleType("Receive")
starlette.types.Send = types.ModuleType("Send")
starlette.types.Lifespan = types.ModuleType("Lifespan")
starlette.types.Message = types.ModuleType("Message")

# Mock other common dependencies
mock_module("base58")

pydantic = mock_module("pydantic")
class BaseModel:
    def dict(self, *args, **kwargs):
        return {}
pydantic.BaseModel = BaseModel
pydantic.Field = lambda *args, **kwargs: None
pydantic.computed_field = lambda *args, **kwargs: lambda f: f
pydantic.validator = lambda *args, **kwargs: lambda f: f
pydantic.field_validator = lambda *args, **kwargs: lambda f: f
pydantic.HttpUrl = str
pydantic.AnyHttpUrl = str
pydantic.UUID4 = str
pydantic.AliasChoices = lambda *args, **kwargs: None
pydantic.SecretStr = str
pydantic.ConfigDict = dict
pydantic.field_serializer = lambda *args, **kwargs: lambda f: f
pydantic.model_validator = lambda *args, **kwargs: lambda f: f
pydantic.Discriminator = lambda *args, **kwargs: None
pydantic.Tag = lambda *args, **kwargs: None
class TypeAdapter:
    def __init__(self, *args, **kwargs):
        pass
    def rebuild(self):
        pass
    def validate_python(self, *args, **kwargs):
        return MagicMock()
    def dump_python(self, *args, **kwargs):
        return {}
pydantic.TypeAdapter = TypeAdapter
pydantic.ValidationError = Exception
pydantic_alias_generators = mock_module("pydantic.alias_generators")
pydantic_alias_generators.to_camel = lambda *args, **kwargs: "camelCase"
pydantic_alias_generators.to_pascal = lambda *args, **kwargs: "PascalCase"
pydantic.alias_generators = pydantic_alias_generators
pydantic.with_config = lambda *args, **kwargs: lambda f: f
pydantic.model_serializer = lambda *args, **kwargs: lambda f: f

pydantic_settings = mock_module("pydantic_settings")
class BaseSettings:
    def dict(self, *args, **kwargs):
        return {}
pydantic_settings.BaseSettings = BaseSettings
pydantic_settings.SettingsConfigDict = dict

tenacity = mock_module("tenacity")
tenacity.retry = lambda *args, **kwargs: lambda f: f
tenacity.stop_after_attempt = lambda *args: None
tenacity.wait_exponential = lambda *args, **kwargs: None
tenacity.retry_if_exception_type = lambda *args: None
class AsyncRetrying:
    def __init__(self, *args, **kwargs):
        pass
    def __aiter__(self):
        return self
    async def __anext__(self):
        raise StopAsyncIteration
tenacity.AsyncRetrying = AsyncRetrying
tenacity.before_sleep_log = lambda *args: None
tenacity.after_log = lambda *args: None

tenacity_wait = mock_module("tenacity.wait")
tenacity_wait.wait_random_exponential = lambda *args, **kwargs: None
tenacity.wait = tenacity_wait
tenacity_retry = mock_module("tenacity.retry")
tenacity.retry_module = tenacity_retry # avoid name collision with function
tenacity_stop = mock_module("tenacity.stop")
tenacity.stop = tenacity_stop
 
mock_module("httpx")
mock_module("aiohttp")
mock_module("aiohttp.web")
mock_module("aiohttp.web_request")
web3 = mock_module("web3")
web3.Web3 = MagicMock()
eth_account = mock_module("eth_account")
eth_account.Account = MagicMock()
eth_account_messages = mock_module("eth_account.messages")
eth_account_messages.encode_defunct = lambda *args, **kwargs: None
x402 = mock_module("x402")
x402.__path__ = []
x402_paywall = mock_module("x402.paywall")
x402_paywall.get_paywall_html = lambda *args, **kwargs: "<html>Paid Content</html>"
x402_facilitator = mock_module("x402.facilitator")
x402_facilitator.FacilitatorClient = MagicMock()
x402_facilitator.FacilitatorConfig = MagicMock()
x402_types = mock_module("x402.types")
x402_types.PaymentPayload = dict
x402_types.PaymentRequirements = dict
x402_types.x402PaymentRequiredResponse = Exception
x402_types.x402PaymentRequiredException = Exception
x402_common = mock_module("x402.common")
x402_common.x402_VERSION = "0.1"
x402_common.find_matching_payment_requirements = lambda *args, **kwargs: None
x402_encoding = mock_module("x402.encoding")
x402_encoding.safe_base64_decode = lambda *args, **kwargs: b""
loguru = mock_module("loguru")
loguru.logger = MagicMock()
mock_module("psutil")
opentelemetry = mock_module("opentelemetry")
opentelemetry.metrics = MagicMock()
opentelemetry_trace = mock_module("opentelemetry.trace")
opentelemetry_trace.Span = MagicMock()
opentelemetry_trace.get_tracer = MagicMock()
opentelemetry_trace.get_current_span = MagicMock()
opentelemetry_trace.use_span = MagicMock()
opentelemetry_trace.Status = MagicMock()
opentelemetry_trace.StatusCode = MagicMock()
mock_module("opentelemetry.api")
mock_module("opentelemetry.api.trace")
mock_module("cryptography")
mock_module("cryptography.hazmat")
cryptography_hazmat_primitives = mock_module("cryptography.hazmat.primitives")
cryptography_hazmat_primitives.serialization = mock_module("cryptography.hazmat.primitives.serialization")
cryptography_hazmat_primitives.hashes = mock_module("cryptography.hazmat.primitives.hashes")
cryptography_hazmat_primitives_asymmetric = mock_module("cryptography.hazmat.primitives.asymmetric")
cryptography_hazmat_primitives_asymmetric.ed25519 = mock_module("cryptography.hazmat.primitives.asymmetric.ed25519")
mock_module("requests")
sqlalchemy = mock_module("sqlalchemy")
sqlalchemy.TIMESTAMP = MagicMock()
sqlalchemy.Column = MagicMock()
sqlalchemy.Integer = MagicMock()
sqlalchemy.String = MagicMock()
sqlalchemy.Boolean = MagicMock()
sqlalchemy.ForeignKey = MagicMock()
sqlalchemy.Table = MagicMock()
sqlalchemy.MetaData = MagicMock()
sqlalchemy.create_engine = MagicMock()
sqlalchemy.select = MagicMock()
sqlalchemy.text = MagicMock()
sqlalchemy.func = MagicMock()
sqlalchemy.and_ = MagicMock()
sqlalchemy.or_ = MagicMock()
sqlalchemy.desc = MagicMock()
sqlalchemy.asc = MagicMock()
sqlalchemy.Index = MagicMock()
mock_module("dateutil")
mock_module("dateutil.parser")

class Request:
    def __init__(self, method, url, headers=None):
        self.method = method
        self.url = MagicMock()
        self.url.path = url
        self.headers = headers or {}

class Response:
    def __init__(self, content=None, status_code=200, headers=None, media_type=None):
        self.body = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type

class JSONResponse(Response):
    pass

class BaseHTTPMiddleware:
    def __init__(self, app):
        self.app = app
    async def dispatch(self, request, call_next):
        pass

starlette.requests.Request = Request
starlette.responses.Response = Response
starlette.responses.JSONResponse = JSONResponse
class HTMLResponse(Response):
    pass
starlette.responses.HTMLResponse = HTMLResponse
starlette.middleware.base.BaseHTTPMiddleware = BaseHTTPMiddleware

# Mock SQLAlchemy
sqlalchemy = mock_module("sqlalchemy")
sqlalchemy.dialects = mock_module("sqlalchemy.dialects")
sqlalchemy.dialects.postgresql = mock_module("sqlalchemy.dialects.postgresql")
sqlalchemy.dialects.postgresql.JSONB = MagicMock()
sqlalchemy.dialects.postgresql.UUID = MagicMock()
sqlalchemy.ext = mock_module("sqlalchemy.ext")
sqlalchemy.ext.asyncio = mock_module("sqlalchemy.ext.asyncio")
mock_module("asyncpg")

# --- Import Actual Modules Under Test ---
try:
    import bindu.server.metrics as metrics_mod
    import bindu.server.middleware.metrics as middleware_mod
    import bindu.server.endpoints.health as health_mod
    print("[SETUP] Modules imported successfully")
except ImportError as e:
    print(f"[SETUP] Import failed: {e}")
    # If it fails, print sys.path to debug
    print(f"sys.path: {sys.path}")
    sys.exit(1)

# --- Verification Tests ---

def test_metrics_singleton_race():
    """Verify get_metrics singleton is thread-safe."""
    print("Testing Metrics Singleton Race Condition...")
    
    # Reset singleton
    metrics_mod._metrics_instance = None
    
    instances = []
    def get_instance():
        time.sleep(0.001) # Small sleep
        instance = metrics_mod.get_metrics()
        instances.append(instance)
        
    threads = []
    for _ in range(20):
        t = threading.Thread(target=get_instance)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    if not instances:
        print("[FAIL] No instances created")
        return

    first_instance = instances[0]
    all_same = all(inst is first_instance for inst in instances)
    if all_same:
        print("[OK] Singleton is thread-safe")
    else:
        print(f"[FAIL] Singleton Race Condition Detected! (Created {len(set(instances))} distinct instances)")

def test_middleware_cardinality():
    """Verify URL sanitization in middleware."""
    print("\nTesting Middleware URL Cardinality...")
    
    metrics = metrics_mod.get_metrics()
    metrics.record_http_request = MagicMock()
    
    # Mock app call_next
    async def mock_call_next(request):
        resp = starlette.responses.Response()
        resp.status_code = 200
        return resp

    # Reset metrics for clean test
    metrics.record_http_request.reset_mock()

    middleware = middleware_mod.MetricsMiddleware(MagicMock())
    
    async def run_test():
        # Test UUID path
        req1 = starlette.requests.Request("GET", "/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000")
        await middleware.dispatch(req1, mock_call_next)
        
        # Test Numeric path
        req2 = starlette.requests.Request("GET", "/api/v1/agents/123/chat")
        await middleware.dispatch(req2, mock_call_next)
        
        # Verify calls
        calls = metrics.record_http_request.call_args_list
        
        if len(calls) < 2:
            print(f"[FAIL] Expected 2 calls, got {len(calls)}")
            return

        # Check call 1
        endpoint1 = calls[0].args[1]
        print(f"  Sanitized UUID path: {endpoint1}")
        if ":id" in endpoint1 and "550e8400" not in endpoint1:
            print("[OK] UUID Sanitized")
        else:
            print(f"[FAIL] UUID Not Sanitized: {endpoint1}")

        # Check call 2
        endpoint2 = calls[1].args[1]
        print(f"  Sanitized Numeric path: {endpoint2}")
        if ":id" in endpoint2 and "123" not in endpoint2:
            print("[OK] Numeric ID Sanitized")
        else:
            print(f"[FAIL] Numeric ID Not Sanitized: {endpoint2}")

    import asyncio
    asyncio.run(run_test())

def test_health_monotonic():
    """Verify health endpoint uses monotonic time."""
    print("\nTesting Health Endpoint Monotonic Time...")

    _start_time = health_mod._start_time
    
    print(f"  _start_time: {_start_time}")
    print(f"  current monotonic: {time.monotonic()}")
    print(f"  current time.time: {time.time()}")

    # _start_time should be monotonic (small float relative to boot, usually < time.time())
    # Note: On some systems monotonic might be large, but usually significantly different from epoch time
    # The key is that we changed it FROM time() TO monotonic()
    
    # Heuristic: monotonic is usually uptime-based (small), time.time is epoch (huge ~1.7e9)
    if _start_time < 1000000000: 
        print(f"[OK] _start_time appears to be monotonic (small value)")
    else:
        # If it's huge, is it close to monotonic?
        if abs(_start_time - time.monotonic()) < 1000:
             print(f"[OK] _start_time matches monotonic clock")
        else:
             print(f"[FAIL] _start_time ({_start_time}) looks like epoch time")

if __name__ == "__main__":
    try:
        test_metrics_singleton_race()
        test_middleware_cardinality()
        test_health_monotonic()
    except Exception as e:
        print(f"\n[FAIL] Tests Failed with error: {e}")
        import traceback
        traceback.print_exc()
