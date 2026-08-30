from pathlib import Path
from typing import Any

from TestcontainersLibrary.lifecycle import ResourceLifecycle
from TestcontainersLibrary.log_capture import FailedTestLogCapture


class FailedTestLogCollector:
    """Collect active container logs when any test in the execution fails."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, artifact_root: str) -> None:
        if not artifact_root:
            raise ValueError("artifact root must not be empty")
        root = Path(artifact_root)
        if root.exists() and not root.is_dir():
            raise ValueError(f"artifact root is not a directory: {root}")
        self._resources = ResourceLifecycle.for_execution()
        self._capture = FailedTestLogCapture(root)

    def end_test(self, data: Any, result: Any) -> None:
        if result.status != "FAIL":
            return
        try:
            suite_name = result.longname.rsplit(".", 1)[0]
            self._capture.write(
                suite_name,
                data.name,
                result.start_time,
                result.end_time,
                self._resources.active_containers(),
            )
        except Exception:  # noqa: BLE001
            # Log collection must never change Robot's test result.
            return


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
