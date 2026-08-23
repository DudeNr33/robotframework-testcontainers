import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from testcontainers.core.container import DockerContainer


class FailedTestLogCapture:
    """Write active containers' logs when a Robot test fails."""

    _run_directories: ClassVar[dict[Path, Path]] = {}

    def __init__(self, artifact_root: Path) -> None:
        self._artifact_root = artifact_root

    def write(
        self,
        suite_name: str,
        test_name: str,
        start_time: datetime,
        end_time: datetime,
        containers: Iterable[DockerContainer],
    ) -> None:
        containers = tuple(containers)
        if not containers:
            return

        artifact_directory = self._artifact_directory(suite_name, test_name, start_time)
        try:
            artifact_directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            return

        for container in containers:
            self._write_container_logs(
                container, artifact_directory, start_time, end_time
            )

    def _artifact_directory(
        self, suite_name: str, test_name: str, start_time: datetime
    ) -> Path:
        run_directory = self._run_directories.get(self._artifact_root)
        if run_directory is None:
            run_directory = self._artifact_root / self._run_timestamp(start_time)
            self._run_directories[self._artifact_root] = run_directory
        return (
            run_directory
            / self._safe_path_component(suite_name)
            / self._safe_path_component(test_name)
        )

    def _write_container_logs(
        self,
        container: DockerContainer,
        artifact_directory: Path,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        try:
            wrapped_container = container.get_wrapped_container()
            name = self._safe_path_component(wrapped_container.name or "container")
            if wrapped_container.id is None:
                raise KeyError(f"No ID found on container object {wrapped_container}.")
            container_id = wrapped_container.id[:12]
            filename = f"{name}-{container_id}"
        except Exception as error:  # noqa: BLE001
            self._write_collection_error(
                artifact_directory / "container.error.txt", error
            )
            return

        for stream in ("stdout", "stderr"):
            try:
                log_bytes = wrapped_container.logs(
                    stdout=stream == "stdout",
                    stderr=stream == "stderr",
                    since=start_time,
                    until=end_time,
                    timestamps=False,
                )
                (artifact_directory / f"{filename}.{stream}.log").write_text(
                    log_bytes.decode("utf-8", errors="replace")
                )
            except Exception as error:  # noqa: BLE001
                self._write_collection_error(
                    artifact_directory / f"{filename}.error.txt", error
                )

    @staticmethod
    def _write_collection_error(path: Path, error: Exception) -> None:
        try:
            path.write_text(f"Could not collect container logs: {error}\n")
        except OSError:
            pass

    @staticmethod
    def _run_timestamp(start_time: datetime) -> str:
        if start_time.tzinfo is None:
            start_time = start_time.astimezone()
        return start_time.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    @staticmethod
    def _safe_path_component(value: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
        return sanitized or "unnamed"
