from fastapi.routing import APIRoute
from starlette.routing import WebSocketRoute
from app.backend.app_factory import create_app
def test_create_app_registers_http_and_websocket_routes() -> None:
    app = create_app()
    http_paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    websocket_paths = {route.path for route in app.routes if isinstance(route, WebSocketRoute)}
    assert "/games" in http_paths
    assert "/analyze" in http_paths
    assert "/health/db" in http_paths
    assert "/ws/analyze" in websocket_paths
