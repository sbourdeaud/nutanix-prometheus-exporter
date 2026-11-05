"""Helpers for Prometheus labels on storage-container metrics."""

from typing import Optional


def format_storage_container_label(parent_name: Optional[str], entity_name: str) -> str:
    """Build the ``<cluster>_<container>`` label used for storage-container series.

    Falls back to the container name alone when ``parent_name`` is missing.
    Dots and hyphens are replaced with underscores for Prometheus compliance.
    """
    storage_container_cluster = parent_name if parent_name else entity_name
    entity = f"{storage_container_cluster}_{entity_name}"
    return entity.replace(".", "_").replace("-", "_")
