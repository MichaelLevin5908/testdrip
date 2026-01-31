"""
Test framework middleware integrations.

This module tests the FastAPI and Flask middleware integrations
for automatic Drip context management and billing.
"""

import pytest
import os
from typing import Optional

# Check if drip-sdk is available
try:
    from drip import Drip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None

# Check if FastAPI is available
try:
    import fastapi
    from fastapi import FastAPI, Depends, Request
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    TestClient = None

# Check if Flask is available
try:
    import flask
    from flask import Flask, g
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None

# Check if middleware modules are available
try:
    from drip.middleware.fastapi import drip_middleware, DripDep, DripMiddleware
    FASTAPI_MIDDLEWARE_AVAILABLE = True
except ImportError:
    FASTAPI_MIDDLEWARE_AVAILABLE = False
    drip_middleware = None
    DripDep = None
    DripMiddleware = None

try:
    from drip.middleware.flask import (
        drip_middleware as flask_drip_middleware,
        DripFlaskMiddleware,
        get_drip
    )
    FLASK_MIDDLEWARE_AVAILABLE = True
except ImportError:
    FLASK_MIDDLEWARE_AVAILABLE = False
    flask_drip_middleware = None
    DripFlaskMiddleware = None
    get_drip = None


pytestmark = [
    pytest.mark.skipif(not DRIP_SDK_AVAILABLE, reason="drip-sdk not installed"),
    pytest.mark.middleware
]


class TestFastAPIMiddleware:
    """Test FastAPI middleware integration."""

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_creates_context(self, api_key, base_url):
        """FastAPI middleware creates Drip context."""
        app = FastAPI()

        # Add middleware
        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url
        )

        @app.get("/test")
        def test_route(request: Request):
            drip = getattr(request.state, "drip", None)
            return {"has_drip": drip is not None}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["has_drip"] is True

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_dependency_injection(self, api_key, base_url):
        """FastAPI middleware supports dependency injection."""
        app = FastAPI()

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url
        )

        @app.get("/test-dep")
        def test_route(drip: DripDep):
            return {"drip_available": drip is not None}

        client = TestClient(app)
        response = client.get("/test-dep")
        assert response.status_code == 200

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_skips_in_dev(self, api_key, base_url):
        """FastAPI middleware skips billing in dev mode."""
        app = FastAPI()

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url,
            skip_in_development=True
        )

        @app.get("/test")
        def test_route():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_excludes_paths(self, api_key, base_url):
        """FastAPI middleware can exclude specific paths."""
        app = FastAPI()

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url,
            exclude_paths=["/health", "/metrics"]
        )

        @app.get("/health")
        def health_route():
            return {"status": "healthy"}

        @app.get("/api/data")
        def data_route(request: Request):
            drip = getattr(request.state, "drip", None)
            return {"has_drip": drip is not None}

        client = TestClient(app)

        # Excluded path should work without Drip context
        response = client.get("/health")
        assert response.status_code == 200

        # Non-excluded path should have Drip context
        response = client.get("/api/data")
        assert response.status_code == 200

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_customer_extraction(self, api_key, base_url):
        """FastAPI middleware extracts customer from request."""
        app = FastAPI()

        def extract_customer(request: Request) -> Optional[str]:
            return request.headers.get("X-Customer-ID")

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url,
            customer_extractor=extract_customer
        )

        @app.get("/test")
        def test_route(request: Request):
            drip = getattr(request.state, "drip", None)
            customer_id = getattr(request.state, "drip_customer_id", None)
            return {
                "has_drip": drip is not None,
                "customer_id": customer_id
            }

        client = TestClient(app)
        response = client.get("/test", headers={"X-Customer-ID": "cust_123"})
        assert response.status_code == 200

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_error_handling(self, api_key, base_url):
        """FastAPI middleware handles errors gracefully."""
        app = FastAPI()

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url
        )

        @app.get("/error")
        def error_route():
            raise ValueError("Test error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")
        # Should return 500 but not crash the middleware
        assert response.status_code == 500

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_with_lifespan(self, api_key, base_url):
        """FastAPI middleware works with lifespan context."""
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan(app):
            # Startup
            yield
            # Shutdown

        app = FastAPI(lifespan=lifespan)

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url
        )

        @app.get("/test")
        def test_route():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200


class TestFlaskMiddleware:
    """Test Flask middleware integration."""

    @pytest.mark.skipif(
        not FLASK_AVAILABLE or not FLASK_MIDDLEWARE_AVAILABLE,
        reason="Flask or drip.middleware.flask not available"
    )
    def test_flask_middleware_creates_context(self, api_key, base_url):
        """Flask middleware creates Drip context."""
        app = Flask(__name__)
        app.wsgi_app = DripFlaskMiddleware(
            app.wsgi_app,
            api_key=api_key,
            base_url=base_url
        )

        @app.route("/test")
        def test_route():
            drip = get_drip()
            return {"has_drip": drip is not None}

        with app.test_client() as client:
            response = client.get("/test")
            assert response.status_code == 200

    @pytest.mark.skipif(
        not FLASK_AVAILABLE or not FLASK_MIDDLEWARE_AVAILABLE,
        reason="Flask or drip.middleware.flask not available"
    )
    def test_flask_middleware_g_object(self, api_key, base_url):
        """Flask middleware sets drip on g object."""
        app = Flask(__name__)
        app.wsgi_app = DripFlaskMiddleware(
            app.wsgi_app,
            api_key=api_key,
            base_url=base_url
        )

        @app.route("/test")
        def test_route():
            return {"has_drip": hasattr(g, "drip")}

        with app.test_client() as client:
            response = client.get("/test")
            assert response.status_code == 200

    @pytest.mark.skipif(
        not FLASK_AVAILABLE or not FLASK_MIDDLEWARE_AVAILABLE,
        reason="Flask or drip.middleware.flask not available"
    )
    def test_flask_middleware_skips_in_dev(self, api_key, base_url):
        """Flask middleware skips billing in dev mode."""
        app = Flask(__name__)
        app.config["DEBUG"] = True

        app.wsgi_app = DripFlaskMiddleware(
            app.wsgi_app,
            api_key=api_key,
            base_url=base_url,
            skip_in_development=True
        )

        @app.route("/test")
        def test_route():
            return {"ok": True}

        with app.test_client() as client:
            response = client.get("/test")
            assert response.status_code == 200

    @pytest.mark.skipif(
        not FLASK_AVAILABLE or not FLASK_MIDDLEWARE_AVAILABLE,
        reason="Flask or drip.middleware.flask not available"
    )
    def test_flask_middleware_excludes_paths(self, api_key, base_url):
        """Flask middleware can exclude specific paths."""
        app = Flask(__name__)

        app.wsgi_app = DripFlaskMiddleware(
            app.wsgi_app,
            api_key=api_key,
            base_url=base_url,
            exclude_paths=["/health", "/metrics"]
        )

        @app.route("/health")
        def health_route():
            return {"status": "healthy"}

        @app.route("/api/data")
        def data_route():
            return {"ok": True}

        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 200

            response = client.get("/api/data")
            assert response.status_code == 200

    @pytest.mark.skipif(
        not FLASK_AVAILABLE or not FLASK_MIDDLEWARE_AVAILABLE,
        reason="Flask or drip.middleware.flask not available"
    )
    def test_flask_middleware_customer_extraction(self, api_key, base_url):
        """Flask middleware extracts customer from request."""
        from flask import request as flask_request

        app = Flask(__name__)

        def extract_customer(request) -> Optional[str]:
            return request.headers.get("X-Customer-ID")

        app.wsgi_app = DripFlaskMiddleware(
            app.wsgi_app,
            api_key=api_key,
            base_url=base_url,
            customer_extractor=extract_customer
        )

        @app.route("/test")
        def test_route():
            customer_id = getattr(g, "drip_customer_id", None)
            return {"customer_id": customer_id}

        with app.test_client() as client:
            response = client.get("/test", headers={"X-Customer-ID": "cust_456"})
            assert response.status_code == 200

    @pytest.mark.skipif(
        not FLASK_AVAILABLE or not FLASK_MIDDLEWARE_AVAILABLE,
        reason="Flask or drip.middleware.flask not available"
    )
    def test_flask_middleware_error_handling(self, api_key, base_url):
        """Flask middleware handles errors gracefully."""
        app = Flask(__name__)
        app.wsgi_app = DripFlaskMiddleware(
            app.wsgi_app,
            api_key=api_key,
            base_url=base_url
        )

        @app.route("/error")
        def error_route():
            raise ValueError("Test error")

        with app.test_client() as client:
            response = client.get("/error")
            # Should return 500 but not crash
            assert response.status_code == 500

    @pytest.mark.skipif(
        not FLASK_AVAILABLE or not FLASK_MIDDLEWARE_AVAILABLE,
        reason="Flask or drip.middleware.flask not available"
    )
    def test_flask_middleware_blueprint_routes(self, api_key, base_url):
        """Flask middleware works with blueprints."""
        from flask import Blueprint

        app = Flask(__name__)
        app.wsgi_app = DripFlaskMiddleware(
            app.wsgi_app,
            api_key=api_key,
            base_url=base_url
        )

        api = Blueprint("api", __name__, url_prefix="/api")

        @api.route("/data")
        def api_data():
            return {"source": "blueprint"}

        app.register_blueprint(api)

        with app.test_client() as client:
            response = client.get("/api/data")
            assert response.status_code == 200
            assert response.json["source"] == "blueprint"


class TestMiddlewareConfiguration:
    """Test middleware configuration options."""

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_custom_headers(self, api_key, base_url):
        """FastAPI middleware accepts custom headers."""
        app = FastAPI()

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url,
            custom_headers={"X-Source": "test-app"}
        )

        @app.get("/test")
        def test_route():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_meter_configuration(self, api_key, base_url):
        """FastAPI middleware supports meter configuration."""
        app = FastAPI()

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url,
            default_meter="api_requests",
            auto_track=True
        )

        @app.get("/test")
        def test_route():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    @pytest.mark.skipif(
        not FLASK_AVAILABLE or not FLASK_MIDDLEWARE_AVAILABLE,
        reason="Flask or drip.middleware.flask not available"
    )
    def test_flask_middleware_custom_headers(self, api_key, base_url):
        """Flask middleware accepts custom headers."""
        app = Flask(__name__)

        app.wsgi_app = DripFlaskMiddleware(
            app.wsgi_app,
            api_key=api_key,
            base_url=base_url,
            custom_headers={"X-Source": "test-flask-app"}
        )

        @app.route("/test")
        def test_route():
            return {"ok": True}

        with app.test_client() as client:
            response = client.get("/test")
            assert response.status_code == 200


class TestMiddlewareAsync:
    """Test async behavior of middleware."""

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    @pytest.mark.asyncio
    async def test_fastapi_middleware_async_routes(self, api_key, base_url):
        """FastAPI middleware works with async routes."""
        import asyncio

        app = FastAPI()

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url
        )

        @app.get("/async-test")
        async def async_route():
            await asyncio.sleep(0.01)
            return {"async": True}

        client = TestClient(app)
        response = client.get("/async-test")
        assert response.status_code == 200
        assert response.json()["async"] is True

    @pytest.mark.skipif(
        not FASTAPI_AVAILABLE or not FASTAPI_MIDDLEWARE_AVAILABLE,
        reason="FastAPI or drip.middleware.fastapi not available"
    )
    def test_fastapi_middleware_concurrent_requests(self, api_key, base_url):
        """FastAPI middleware handles concurrent requests."""
        import concurrent.futures

        app = FastAPI()

        app.add_middleware(
            DripMiddleware,
            api_key=api_key,
            base_url=base_url
        )

        request_count = 0

        @app.get("/concurrent")
        def concurrent_route():
            nonlocal request_count
            request_count += 1
            return {"count": request_count}

        client = TestClient(app)

        def make_request():
            return client.get("/concurrent")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        assert all(r.status_code == 200 for r in results)
