"""Minimal tests for auth middleware base."""

from unittest.mock import Mock

from bindu.server.middleware.auth.base import AuthMiddleware


class TestAuthMiddlewareBase:
    """Test auth middleware base functionality."""

    def test_is_public_endpoint_matches_pattern(self):
        """Test public endpoint pattern matching."""
        mock_config = Mock()
        mock_config.public_endpoints = ["/health", "/metrics", "/api/public/*"]

        # Create a concrete implementation for testing
        class TestAuthMiddleware(AuthMiddleware):
            def _initialize_provider(self):
                pass

            def _validate_token(self, token):
                return {}

            def _extract_user_info(self, token_payload):
                return {}

        middleware = TestAuthMiddleware(app=Mock(), auth_config=mock_config)

        assert middleware._is_public_endpoint("/health") is True
        assert middleware._is_public_endpoint("/metrics") is True
        assert middleware._is_public_endpoint("/api/public/test") is True
        assert middleware._is_public_endpoint("/api/private/test") is False

    def test_extract_token_from_header(self):
        """Test extracting token from Authorization header."""
        mock_config = Mock()
        mock_config.public_endpoints = []

        class TestAuthMiddleware(AuthMiddleware):
            def _initialize_provider(self):
                pass

            def _validate_token(self, token):
                return {}

            def _extract_user_info(self, token_payload):
                return {}

        middleware = TestAuthMiddleware(app=Mock(), auth_config=mock_config)

        mock_conn = Mock()
        mock_conn.headers = {"Authorization": "Bearer test-token-123"}
        mock_conn.scope = {"type": "http"}

        token = middleware._extract_token(mock_conn)

        assert token == "test-token-123"

    def test_extract_token_from_query_params(self):
        """Test extracting token from query parameters."""
        mock_config = Mock()
        mock_config.public_endpoints = []

        class TestAuthMiddleware(AuthMiddleware):
            def _initialize_provider(self):
                pass

            def _validate_token(self, token):
                return {}

            def _extract_user_info(self, token_payload):
                return {}

        middleware = TestAuthMiddleware(app=Mock(), auth_config=mock_config)

        mock_conn = Mock()
        mock_conn.headers = {}
        mock_conn.query_params = {"token": "query-token-456"}
        mock_conn.scope = {"type": "http"}

        token = middleware._extract_token(mock_conn)

        assert token == "query-token-456"

    def test_extract_token_returns_none_when_missing(self):
        """Test that None is returned when no token is present."""
        mock_config = Mock()
        mock_config.public_endpoints = []

        class TestAuthMiddleware(AuthMiddleware):
            def _initialize_provider(self):
                pass

            def _validate_token(self, token):
                return {}

            def _extract_user_info(self, token_payload):
                return {}

        middleware = TestAuthMiddleware(app=Mock(), auth_config=mock_config)

        mock_conn = Mock()
        mock_conn.headers = {}
        mock_conn.query_params = {}
        mock_conn.scope = {"type": "http"}

        token = middleware._extract_token(mock_conn)

        assert token is None

    def test_attach_user_context(self):
        """Test attaching user context to ASGI scope."""
        mock_config = Mock()
        mock_config.public_endpoints = []

        class TestAuthMiddleware(AuthMiddleware):
            def _initialize_provider(self):
                pass

            def _validate_token(self, token):
                return {}

            def _extract_user_info(self, token_payload):
                return {}

        middleware = TestAuthMiddleware(app=Mock(), auth_config=mock_config)

        scope = {}
        user_info = {"sub": "user123", "email": "test@example.com"}
        token_payload = {"exp": 1234567890}

        middleware._attach_user_context(scope, user_info, token_payload)

        assert scope["state"]["user"] == user_info
        assert scope["state"]["authenticated"] is True
        assert scope["state"]["token_payload"] == token_payload
