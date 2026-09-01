from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from TestcontainersLibrary.lifecycle import ResourceLifecycle
from TestcontainersLibrary.log_capture import FailedTestLogCapture, safe_path_component


class FailedTestLogCollector:
    """Collect active container logs when any test in the execution fails."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, artifact_root: str | None = None) -> None:
        if artifact_root == "":
            raise ValueError("artifact root must not be empty")

        root = Path(artifact_root) if artifact_root is not None else None
        if root is not None and not root.is_absolute():
            root = Path.cwd() / root
        if root is not None and root.exists() and not root.is_dir():
            raise ValueError(f"artifact root is not a directory: {root}")

        self._resources = ResourceLifecycle.for_execution()
        self._artifact_root = root
        self._run_directory: Path | None = None
        self._capture = FailedTestLogCapture()

    def end_test(self, data: Any, result: Any) -> None:
        if result.status != "FAIL":
            return
        try:
            artifact_directory = self._artifact_directory(data, result)
            wrote_artifact = self._capture.write(
                artifact_directory,
                result.start_time,
                result.end_time,
                self._resources.active_containers(),
            )
            if wrote_artifact:
                logger.info(
                    "TestcontainersLibrary: failed-test container logs written to "
                    f"{artifact_directory}"
                )
        except Exception:  # noqa: BLE001
            # Log collection must never change Robot's test result.
            return

    def _artifact_directory(self, data: Any, result: Any) -> Path:
        if self._run_directory is None:
            self._run_directory = self._artifact_root_for_execution() / self._timestamp(
                result.start_time
            )

        directory = self._run_directory
        for suite_name in self._suite_names(result):
            directory /= safe_path_component(suite_name)
        return directory / safe_path_component(data.name)

    def _artifact_root_for_execution(self) -> Path:
        if self._artifact_root is None:
            output_directory = cast(str, BuiltIn().get_variable_value("${OUTPUT_DIR}"))
            self._artifact_root = Path(output_directory) / "container-logs"
        return self._artifact_root

    @staticmethod
    def _suite_names(result: Any) -> list[str]:
        # Suite names can contain dots, so splitting longname would lose the
        # boundaries in Robot's logical suite hierarchy.
        names: list[str] = []
        suite = result.parent
        while suite is not None:
            names.append(suite.name)
            suite = suite.parent
        names.reverse()
        return names

    @staticmethod
    def _timestamp(start_time: datetime) -> str:
        if start_time.tzinfo is None:
            start_time = start_time.astimezone()
        return start_time.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


class LifecycleListener:
    """Forward Robot Framework lifecycle events to resource cleanup."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, resources: ResourceLifecycle) -> None:
        self._resources = resources

    def start_suite(self, data: Any, result: Any) -> None:
        self._resources.enter_suite(result.longname)

    def start_test(self, data: Any, result: Any) -> None:
        self._resources.enter_test(result.longname)

    def end_test(self, data: Any, result: Any) -> None:
        try:
            self._resources.cleanup_test(result.longname)
        finally:
            self._resources.clear_owner()

    def end_suite(self, data: Any, result: Any) -> None:
        try:
            self._resources.cleanup_suite(result.longname)
        finally:
            self._resources.clear_owner()
