"""Catalog department entrypoint: tutors + students + search.

Search used to be its own service backed by ElasticSearch, kept in sync via a
Kafka reindex. It is now just another route prefix in this same department,
reading the Tutors module's own table through Postgres full-text search — see
``modules/search/api/routes/search.py`` and
``modules/tutors/models/tutor.py::search_vector``.
"""

from __future__ import annotations

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .events import bus
from .modules.search.api.routes import search as search_routes
from .modules.students.api.routes import students as students_routes
from .modules.tutors import events as tutors_events  # noqa: F401 — registers handlers
from .modules.tutors.api.routes import tutors as tutors_routes

settings = get_settings()

app = create_app(
    title="EduBridge Catalog Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/tutors", "/students", "/search"],
    routers=[tutors_routes.router, students_routes.router, search_routes.router],
    log_level=settings.log_level,
    on_startup=[bus.start_producer, bus.start_consuming],
    on_shutdown=[bus.stop],
)
