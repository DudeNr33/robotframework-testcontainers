from typing import Any

from TestcontainersLibrary.lifecycle import ResourceLifecycle


class LifecycleListener:
    """Forward Robot Framework lifecycle events to resource cleanup."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, resources: ResourceLifecycle) -> None:
        self._resources = resources

    def end_test(self, data: Any, result: Any) -> None:
        self._resources.cleanup("end_test")

    def end_suite(self, data: Any, result: Any) -> None:
        self._resources.cleanup("end_suite")
