"""Side-effect import module: register all built-in adapters.

Importing this package is the canonical way to populate the adapter registry
without each caller having to import every concrete adapter module.
"""
from app.datasources import (  # noqa: F401  (import for side effects)
    elasticsearch_adapter,
    mysql_adapter,
    postgres_adapter,
    vector_db_adapter,
)


def all_types() -> list[str]:
    from app.datasources.base import list_datasource_types

    return list_datasource_types()