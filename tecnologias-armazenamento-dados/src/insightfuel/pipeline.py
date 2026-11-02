from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .backends import GcpBackend
from .config import Settings
from .transform import read_and_clean_source_files


class PipelineBackend(Protocol):
    def local_files(self, source: str) -> list[Path]: ...
    def upload_files(self, source: str, run_id: str, files: list[Path], status: str = "incoming") -> list[str]: ...
    def read_objects(self, object_uris: list[str]) -> list[tuple[str, bytes]]: ...
    def move_objects(self, object_uris: list[str], destination_status: str) -> list[str]: ...
    def replace_source(self, source: str, rows: list[dict[str, object]]) -> int: ...
    def validate_silver(self) -> dict[str, int]: ...
    def generate_gold(self) -> int: ...
    def validate_gold(self) -> dict[str, int]: ...
    def record_event(self, **kwargs) -> None: ...


def backend_for(settings: Settings) -> PipelineBackend:
    return GcpBackend(settings)


def validate_layout(
    settings: Settings,
    source: str,
    run_id: str,
    backend: PipelineBackend | None = None,
) -> list[str]:
    backend = backend or backend_for(settings)
    files = backend.local_files(source)
    try:
        rows = read_and_clean_source_files(source, [(path.name, path.read_bytes()) for path in files])
    except Exception as exc:
        rejected = backend.upload_files(source, run_id, files, status="rejected")
        for path, uri in zip(files, rejected):
            backend.record_event(
                run_id=run_id, source=source, stage="layout", status="rejected",
                file_name=path.name, object_uri=uri, details=str(exc),
            )
        raise
    backend.record_event(
        run_id=run_id, source=source, stage="layout", status="validated", row_count=len(rows)
    )
    return [str(path) for path in files]


def ingest_bronze(
    settings: Settings,
    source: str,
    run_id: str,
    validated_files: list[str],
    backend: PipelineBackend | None = None,
) -> list[str]:
    backend = backend or backend_for(settings)
    paths = [Path(path) for path in validated_files]
    uris = backend.upload_files(source, run_id, paths, status="incoming")
    for path, uri in zip(paths, uris):
        backend.record_event(
            run_id=run_id, source=source, stage="bronze", status="uploaded",
            file_name=path.name, object_uri=uri,
        )
    return uris


def process_silver(
    settings: Settings,
    source: str,
    run_id: str,
    object_uris: list[str],
    backend: PipelineBackend | None = None,
) -> int:
    backend = backend or backend_for(settings)
    try:
        rows = read_and_clean_source_files(source, backend.read_objects(object_uris))
        count = backend.replace_source(source, rows)
    except Exception as exc:
        backend.move_objects(object_uris, "rejected")
        backend.record_event(
            run_id=run_id, source=source, stage="silver", status="rejected", details=str(exc)
        )
        raise
    backend.record_event(
        run_id=run_id, source=source, stage="silver", status="loaded", row_count=count
    )
    return count


def validate_quality(settings: Settings, run_id: str, backend: PipelineBackend | None = None) -> dict[str, int]:
    backend = backend or backend_for(settings)
    metrics = backend.validate_silver()
    backend.record_event(
        run_id=run_id, source="all", stage="silver_quality", status="passed",
        row_count=sum(metrics.values()), details=str(metrics),
    )
    return metrics


def generate_gold(settings: Settings, run_id: str, backend: PipelineBackend | None = None) -> int:
    backend = backend or backend_for(settings)
    count = backend.generate_gold()
    backend.record_event(
        run_id=run_id, source="all", stage="gold", status="loaded", row_count=count
    )
    return count


def validate_gold(settings: Settings, run_id: str, backend: PipelineBackend | None = None) -> dict[str, int]:
    backend = backend or backend_for(settings)
    metrics = backend.validate_gold()
    backend.record_event(
        run_id=run_id, source="all", stage="gold_quality", status="passed",
        row_count=metrics["rows"], details=str(metrics),
    )
    return metrics


def archive_bronze(
    settings: Settings,
    run_id: str,
    source_objects: dict[str, list[str]],
    backend: PipelineBackend | None = None,
) -> dict[str, list[str]]:
    backend = backend or backend_for(settings)
    archived = {}
    for source, uris in source_objects.items():
        archived[source] = backend.move_objects(uris, "archive")
        for uri in archived[source]:
            backend.record_event(
                run_id=run_id,
                source=source,
                stage="bronze",
                status="archived",
                file_name=Path(uri).name,
                object_uri=uri,
                row_count=1,
            )
    return archived
