from datetime import datetime, timedelta, timezone
from pathlib import Path

from TestcontainersLibrary.log_capture import FailedTestLogCapture


class FakeContainer:
    def __init__(
        self, name: str, container_id: str, fail_to_return_logs: bool = False
    ) -> None:
        self.name = name
        self.id = container_id
        self.fail_to_return_logs = fail_to_return_logs
        self.calls: list[dict[str, object]] = []

    def get_wrapped_container(self) -> "FakeContainer":
        return self

    def logs(self, **kwargs: object) -> bytes:
        self.calls.append(kwargs)
        if self.fail_to_return_logs:
            raise RuntimeError("cannot read logs")
        return b"stdout" if kwargs["stdout"] else b"stderr"


def test_writes_active_container_streams_in_safe_artifact_paths(tmp_path: Path) -> None:
    capture = FailedTestLogCapture(tmp_path)
    container = FakeContainer("web/api", "abcdef1234567890")
    start = datetime.now(timezone.utc)

    capture.write(
        "Suite",
        "fails / here",
        start,
        start + timedelta(seconds=1),
        [container],  # type: ignore[list-item]
    )

    artifacts = list(tmp_path.glob("**/*.log"))
    assert {artifact.name for artifact in artifacts} == {
        "web-api-abcdef123456.stdout.log",
        "web-api-abcdef123456.stderr.log",
    }
    assert {artifact.read_text() for artifact in artifacts} == {"stdout", "stderr"}
    assert all(call["since"] == start for call in container.calls)


def test_container_log_failure_does_not_block_later_containers(
    tmp_path: Path,
) -> None:
    capture = FailedTestLogCapture(tmp_path)
    failing = FakeContainer("failing", "1111111111111111", fail_to_return_logs=True)
    later = FakeContainer("later", "2222222222222222")
    start = datetime.now(timezone.utc)

    capture.write(
        "Suite",
        "fails",
        start,
        start + timedelta(seconds=1),
        [failing, later],  # type: ignore[list-item]
    )

    artifacts = list(tmp_path.glob("**/*"))
    assert {artifact.name for artifact in artifacts if artifact.is_file()} == {
        "failing-111111111111.error.txt",
        "later-222222222222.stdout.log",
        "later-222222222222.stderr.log",
    }
    assert len(failing.calls) == 2
    assert len(later.calls) == 2


def test_preserves_naive_robot_timestamps_for_log_collection(tmp_path: Path) -> None:
    capture = FailedTestLogCapture(tmp_path)
    container = FakeContainer("local-time", "abcdef1234567890")
    start = datetime.now(timezone.utc).astimezone().replace(tzinfo=None)

    capture.write(
        "Suite",
        "fails",
        start,
        start + timedelta(seconds=1),
        [container],  # type: ignore[list-item]
    )

    assert all(call["since"] == start for call in container.calls)


def test_shares_a_run_directory_between_test_scoped_instances(tmp_path: Path) -> None:
    start = datetime.now(timezone.utc)
    first = FailedTestLogCapture(tmp_path)
    second = FailedTestLogCapture(tmp_path)

    first.write(
        "Suite",
        "first",
        start,
        start + timedelta(seconds=1),
        [FakeContainer("first", "abcdef1234567890")],  # type: ignore[list-item]
    )
    second.write(
        "Suite",
        "second",
        start,
        start + timedelta(seconds=1),
        [FakeContainer("second", "fedcba0987654321")],  # type: ignore[list-item]
    )

    assert len(list(tmp_path.iterdir())) == 1
