import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

from testcontainers.core.container import DockerContainer


def safe_path_component(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return sanitized or "unnamed"


class FailedTestLogCapture:
    """Write active containers' logs when a Robot test fails."""

    _time_tolerance = timedelta(seconds=1)

    def write(
        self,
        artifact_directory: Path,
        start_time: datetime,
        end_time: datetime,
        containers: Iterable[DockerContainer],
    ) -> bool:
        containers = tuple(containers)
        if not containers:
            return False

        try:
            artifact_directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False

        wrote_artifact = False
        for container in containers:
            wrote_artifact = (
                self._write_container_logs(
                    container, artifact_directory, start_time, end_time
                )
                or wrote_artifact
            )
        return wrote_artifact

    def _write_container_logs(
        self,
        container: DockerContainer,
        artifact_directory: Path,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        try:
            wrapped_container = container.get_wrapped_container()
            name = safe_path_component(wrapped_container.name or "container")
            if wrapped_container.id is None:
                raise KeyError(f"No ID found on container object {wrapped_container}.")
            container_id = wrapped_container.id[:12]
            filename = f"{name}-{container_id}"
        except Exception as error:  # noqa: BLE001
            return self._write_collection_error(
                artifact_directory / "container.error.txt", error
            )

        wrote_artifact = False
        for stream in ("stdout", "stderr"):
            try:
                log_bytes = wrapped_container.logs(
                    stdout=stream == "stdout",
                    stderr=stream == "stderr",
                    since=start_time - self._time_tolerance,
                    until=end_time + self._time_tolerance,
                    timestamps=False,
                )
                (artifact_directory / f"{filename}.{stream}.log").write_text(
                    log_bytes.decode("utf-8", errors="replace")
                )
                wrote_artifact = True
            except Exception as error:  # noqa: BLE001
                wrote_artifact = (
                    self._write_collection_error(
                        artifact_directory / f"{filename}.error.txt", error
                    )
                    or wrote_artifact
                )
        return wrote_artifact

    @staticmethod
    def _write_collection_error(path: Path, error: Exception) -> bool:
        try:
            path.write_text(f"Could not collect container logs: {error}\n")
        except OSError:
            return False
        return True
