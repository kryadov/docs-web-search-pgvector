from fastapi.routing import APIRoute

from rag_system.api import api_router


def _api_routes() -> list[APIRoute]:
    return [route for route in api_router.routes if isinstance(route, APIRoute)]


def test_documents_update_route_exists() -> None:
    routes = _api_routes()

    assert any(route.path == "/api/documents/{document_id}" and "PUT" in route.methods for route in routes)


def test_documents_delete_route_exists_with_204_status() -> None:
    routes = _api_routes()
    delete_route = next(
        route for route in routes if route.path == "/api/documents/{document_id}" and "DELETE" in route.methods
    )

    assert delete_route.status_code == 204