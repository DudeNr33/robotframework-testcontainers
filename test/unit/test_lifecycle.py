import pytest

from TestcontainersLibrary import lifecycle
from TestcontainersLibrary.lifecycle import ResourceLifecycle
from TestcontainersLibrary.listener import LifecycleListener


class FakeContainer:
    def __init__(self, fail_to_start: bool = False) -> None:
        self.fail_to_start = fail_to_start
        self.started = False
        self.stop_calls = 0
        self.name = "fake-container"

    def start(self) -> None:
        if self.fail_to_start:
            raise RuntimeError("cannot start")
        self.started = True

    def stop(self) -> None:
        self.stop_calls += 1

    def get_wrapped_container(self) -> "FakeContainer":
        return self


class FakeNetwork:
    def __init__(self) -> None:
        self.id = "fake-network"
        self.created = False
        self.remove_calls = 0

    def create(self) -> None:
        self.created = True

    def remove(self) -> None:
        self.remove_calls += 1


def test_start_tracks_successful_container() -> None:
    resources = ResourceLifecycle()
    container = FakeContainer()

    result = resources.start_container(container)  # type: ignore[arg-type]

    assert result is container  # type: ignore[comparison-overlap]
    assert container.started
    resources.cleanup("end_test")
    assert container.stop_calls == 1


def test_stop_removes_container_from_automatic_cleanup() -> None:
    resources = ResourceLifecycle()
    container = FakeContainer()
    resources.start_container(container)  # type: ignore[arg-type]

    resources.stop_container(container)  # type: ignore[arg-type]
    assert container.stop_calls == 1

    resources.cleanup("end_test")
    assert container.stop_calls == 1


def test_start_failure_stops_untracked_container() -> None:
    resources = ResourceLifecycle()
    container = FakeContainer(fail_to_start=True)

    with pytest.raises(RuntimeError, match="cannot start"):
        resources.start_container(container)  # type: ignore[arg-type]

    assert container.stop_calls == 1

    resources.cleanup("end_test")
    assert container.stop_calls == 1


def test_cleanup_stops_containers_and_removes_networks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = ResourceLifecycle()
    container = FakeContainer()
    network = FakeNetwork()
    resources.start_container(container)  # type: ignore[arg-type]
    monkeypatch.setattr(lifecycle, "Network", lambda: network)
    result = resources.create_network()

    resources.cleanup("end_suite")

    assert result is network  # type: ignore[comparison-overlap]
    assert network.created
    assert container.stop_calls == 1
    assert network.remove_calls == 1


def test_remove_network_removes_it_from_automatic_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = ResourceLifecycle()
    network = FakeNetwork()
    monkeypatch.setattr(lifecycle, "Network", lambda: network)
    resources.create_network()

    resources.remove_network(network)  # type: ignore[arg-type]
    assert network.remove_calls == 1

    resources.cleanup("end_test")
    assert network.remove_calls == 1


def test_listener_delegates_test_and_suite_cleanup() -> None:
    resources = CleanupRecorder()
    listener = LifecycleListener(resources)  # type: ignore[arg-type]

    listener.end_test(None, None)
    listener.end_suite(None, None)

    assert resources.hooks == ["end_test", "end_suite"]


class CleanupRecorder:
    def __init__(self) -> None:
        self.hooks: list[str] = []

    def cleanup(self, hook: str) -> None:
        self.hooks.append(hook)
