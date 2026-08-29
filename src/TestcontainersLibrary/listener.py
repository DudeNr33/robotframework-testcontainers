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

    def start_suite(self, data: Any, result: Any) -> None:
        self._resources.enter_suite(result.longname)

    def start_test(self, data: Any, result: Any) -> None:
        self._resources.enter_test(result.longname)

    def end_test(self, data: Any, result: Any) -> None:
        try:
            if self._failed_log_capture is not None and result.status == "FAIL":
                suite_name = result.longname.rsplit(".", 1)[0]
                self._failed_log_capture.write(
                    suite_name,
                    data.name,
                    result.start_time,
                    result.end_time,
                    self._resources.active_containers(),
                )
            self._resources.cleanup_test(result.longname)
        finally:
            self._resources.clear_owner()

    def end_suite(self, data: Any, result: Any) -> None:
        try:
            self._resources.cleanup_suite(result.longname)
        finally:
            self._resources.clear_owner()
