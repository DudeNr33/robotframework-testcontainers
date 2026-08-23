from typing import Any

from TestcontainersLibrary.lifecycle import ResourceLifecycle
from TestcontainersLibrary.log_capture import FailedTestLogCapture


class LifecycleListener:
    """Forward Robot Framework lifecycle events to resource cleanup."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(
        self,
        resources: ResourceLifecycle,
        failed_log_capture: FailedTestLogCapture | None = None,
    ) -> None:
        self._resources = resources
        self._failed_log_capture = failed_log_capture

    def end_test(self, data: Any, result: Any) -> None:
        if self._failed_log_capture is not None and result.status == "FAIL":
            suite_name = result.longname.rsplit(".", 1)[0]
            self._failed_log_capture.write(
                suite_name,
                data.name,
                result.start_time,
                result.end_time,
                self._resources.active_containers(),
            )
        self._resources.cleanup("end_test")

    def end_suite(self, data: Any, result: Any) -> None:
        self._resources.cleanup("end_suite")
