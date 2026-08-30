from types import SimpleNamespace

import pytest

from TestcontainersLibrary import lifecycle
from TestcontainersLibrary.lifecycle import ResourceLifecycle
from TestcontainersLibrary.listener import LifecycleListener


class FakeContainer:
    def __init__(self, fail_to_start: bool = False, fail_to_stop: bool = False) -> None:
        self.fail_to_start = fail_to_start
        self.fail_to_stop = fail_to_stop
        self.started = False
        self.stop_calls = 0
        self.name = "fake-container"

    def start(self) -> None:
        if self.fail_to_start:
            raise RuntimeError("cannot start")
        self.started = True

    def stop(self) -> None:
        self.stop_calls += 1
        if self.fail_to_stop:
            raise RuntimeError("cannot stop")

    def get_wrapped_container(self) -> "FakeContainer":
        return self


class FakeNetwork:
    def __init__(self, fail_to_remove: bool = False) -> None:
        self.id = "fake-network"
        self.created = False
        self.fail_to_remove = fail_to_remove
        self.remove_attempts = 0
        self.remove_calls = 0
        self.active_container: FakeContainer | None = None

    def create(self) -> None:
        self.created = True

    def remove(self) -> None:
        self.remove_attempts += 1
        if self.fail_to_remove:
            raise RuntimeError("cannot remove")
        if self.active_container is not None and self.active_container.stop_calls == 0:
            raise RuntimeError("network has active endpoints")
        self.remove_calls += 1


def test_start_tracks_successful_container() -> None:
    resources = ResourceLifecycle()
    container = FakeContainer()
    resources.enter_test("Suite.test")

    result = resources.start_container(container)  # type: ignore[arg-type]

    assert result is container  # type: ignore[comparison-overlap]
    assert container.started
    resources.cleanup("end_test")
    assert container.stop_calls == 1


def test_stop_removes_container_from_automatic_cleanup() -> None:
    resources = ResourceLifecycle()
    container = FakeContainer()
    resources.enter_test("Suite.test")
    resources.start_container(container)  # type: ignore[arg-type]

    resources.stop_container(container)  # type: ignore[arg-type]
    assert container.stop_calls == 1

    resources.cleanup("end_test")
    assert container.stop_calls == 1


def test_failed_manual_stop_leaves_container_tracked_for_cleanup() -> None:
    resources = ResourceLifecycle()
    container = FakeContainer(fail_to_stop=True)
    resources.enter_test("Suite.test")
    resources.start_container(container)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="cannot stop"):
        resources.stop_container(container)  # type: ignore[arg-type]

    container.fail_to_stop = False
    resources.cleanup_test("Suite.test")

    assert container.stop_calls == 2
    assert resources.active_containers() == ()


def test_cleanup_only_stops_resources_owned_by_ended_test() -> None:
    resources = ResourceLifecycle()
    suite_container = FakeContainer()
    test_container = FakeContainer()

    resources.enter_suite("Suite")
    resources.start_container(suite_container)  # type: ignore[arg-type]
    resources.enter_test("Suite.test")
    resources.start_container(test_container)  # type: ignore[arg-type]

    resources.cleanup_test("Suite.test")

    assert test_container.stop_calls == 1
    assert suite_container.stop_calls == 0
    assert resources.active_containers() == (suite_container,)  # type: ignore[comparison-overlap]

    resources.cleanup_suite("Suite")
    assert suite_container.stop_calls == 1


def test_start_rejects_container_without_active_owner() -> None:
    resources = ResourceLifecycle()
    container = FakeContainer()

    with pytest.raises(RuntimeError, match="only be started during Robot"):
        resources.start_container(container)  # type: ignore[arg-type]

    assert not container.started
    assert container.stop_calls == 0


def test_start_failure_stops_untracked_container() -> None:
    resources = ResourceLifecycle()
    container = FakeContainer(fail_to_start=True)
    resources.enter_test("Suite.test")

    with pytest.raises(RuntimeError, match="cannot start"):
        resources.start_container(container)  # type: ignore[arg-type]

    assert container.stop_calls == 1

    resources.cleanup("end_test")
    assert container.stop_calls == 1


def test_cleanup_continues_after_container_failure_and_retains_it_for_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = ResourceLifecycle()
    failing_container = FakeContainer(fail_to_stop=True)
    later_container = FakeContainer()
    network = FakeNetwork()
    monkeypatch.setattr(lifecycle, "Network", lambda: network)
    resources.enter_test("Suite.test")
    resources.start_container(failing_container)  # type: ignore[arg-type]
    resources.start_container(later_container)  # type: ignore[arg-type]
    resources.create_network()

    with pytest.raises(RuntimeError, match="cannot stop"):
        resources.cleanup_test("Suite.test")

    assert failing_container.stop_calls == 1
    assert later_container.stop_calls == 1
    assert network.remove_calls == 1
    assert resources.active_containers() == (failing_container,)  # type: ignore[comparison-overlap]


def test_cleanup_continues_after_network_failure_and_retries_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = ResourceLifecycle()
    failing_network = FakeNetwork(fail_to_remove=True)
    later_network = FakeNetwork()
    networks = iter((failing_network, later_network))
    monkeypatch.setattr(lifecycle, "Network", lambda: next(networks))
    resources.enter_test("Suite.test")
    resources.create_network()
    resources.create_network()

    with pytest.raises(RuntimeError, match="cannot remove"):
        resources.cleanup_test("Suite.test")

    assert failing_network.remove_attempts == 1
    assert later_network.remove_calls == 1

    failing_network.fail_to_remove = False
    resources.cleanup_test("Suite.test")

    assert failing_network.remove_calls == 1
    assert later_network.remove_calls == 1


def test_cleanup_stops_containers_and_removes_networks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = ResourceLifecycle()
    container = FakeContainer()
    network = FakeNetwork()
    resources.enter_suite("Suite")
    resources.start_container(container)  # type: ignore[arg-type]
    monkeypatch.setattr(lifecycle, "Network", lambda: network)
    result = resources.create_network()

    resources.cleanup("end_suite")

    assert result is network  # type: ignore[comparison-overlap]
    assert network.created
    assert container.stop_calls == 1
    assert network.remove_calls == 1


def test_cleanup_stops_containers_before_removing_networks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = ResourceLifecycle()
    container = FakeContainer()
    network = FakeNetwork()
    network.active_container = container
    monkeypatch.setattr(lifecycle, "Network", lambda: network)

    resources.enter_test("Suite.test")
    resources.create_network()
    resources.start_container(container)  # type: ignore[arg-type]

    resources.cleanup_test("Suite.test")

    assert container.stop_calls == 1
    assert network.remove_calls == 1


def test_remove_network_removes_it_from_automatic_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = ResourceLifecycle()
    network = FakeNetwork()
    monkeypatch.setattr(lifecycle, "Network", lambda: network)
    resources.enter_test("Suite.test")
    resources.create_network()

    resources.remove_network(network)  # type: ignore[arg-type]
    assert network.remove_calls == 1

    resources.cleanup("end_test")
    assert network.remove_calls == 1


def test_failed_manual_network_removal_leaves_network_tracked_for_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = ResourceLifecycle()
    network = FakeNetwork(fail_to_remove=True)
    monkeypatch.setattr(lifecycle, "Network", lambda: network)
    resources.enter_test("Suite.test")
    resources.create_network()

    with pytest.raises(RuntimeError, match="cannot remove"):
        resources.remove_network(network)  # type: ignore[arg-type]

    network.fail_to_remove = False
    resources.cleanup_test("Suite.test")

    assert network.remove_attempts == 2
    assert network.remove_calls == 1


def test_listener_records_resource_owners_and_cleans_them() -> None:
    resources = CleanupRecorder()
    listener = LifecycleListener(resources)  # type: ignore[arg-type]
    suite = SimpleNamespace(longname="Suite")
    test = SimpleNamespace(
        status="FAIL", longname="Suite.test", start_time="start", end_time="end"
    )

    listener.start_suite(None, suite)
    listener.start_test(None, test)
    listener.end_test(SimpleNamespace(name="test"), test)
    listener.end_suite(None, suite)

    assert resources.events == [
        ("enter_suite", "Suite"),
        ("enter_test", "Suite.test"),
        ("cleanup_test", "Suite.test"),
        ("clear_owner", ""),
        ("cleanup_suite", "Suite"),
        ("clear_owner", ""),
    ]


class CleanupRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def enter_suite(self, longname: str) -> None:
        self.events.append(("enter_suite", longname))

    def enter_test(self, longname: str) -> None:
        self.events.append(("enter_test", longname))

    def clear_owner(self) -> None:
        self.events.append(("clear_owner", ""))

    def active_containers(self) -> tuple[object, ...]:
        return ()

    def cleanup_test(self, longname: str) -> None:
        self.events.append(("cleanup_test", longname))

    def cleanup_suite(self, longname: str) -> None:
        self.events.append(("cleanup_suite", longname))
