from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

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


def test_writes_active_container_streams_to_given_artifact_directory(
    tmp_path: Path,
) -> None:
    capture = FailedTestLogCapture()
    container = FakeContainer("web/api", "abcdef1234567890")
    start = datetime.now(timezone.utc)
    artifact_directory = tmp_path / "complete" / "artifact" / "path"

    wrote_artifact = capture.write(
        artifact_directory,
        start,
        start + timedelta(seconds=1),
        [container],  # type: ignore[list-item]
    )

    assert wrote_artifact
    artifacts = list(artifact_directory.glob("*.log"))
    assert {artifact.name for artifact in artifacts} == {
        "web_api-abcdef123456.stdout.log",
        "web_api-abcdef123456.stderr.log",
    }
    assert {artifact.read_text() for artifact in artifacts} == {"stdout", "stderr"}
    assert all(
        call["since"] == start - timedelta(seconds=1) for call in container.calls
    )
    assert all(
        call["until"] == start + timedelta(seconds=2) for call in container.calls
    )


def test_container_log_failure_does_not_block_later_containers(
    tmp_path: Path,
) -> None:
    capture = FailedTestLogCapture()
    failing = FakeContainer("failing", "1111111111111111", fail_to_return_logs=True)
    later = FakeContainer("later", "2222222222222222")
    start = datetime.now(timezone.utc)

    wrote_artifact = capture.write(
        tmp_path / "artifacts",
        start,
        start + timedelta(seconds=1),
        [failing, later],  # type: ignore[list-item]
    )

    assert wrote_artifact
    artifacts = list(tmp_path.glob("**/*"))
    assert {artifact.name for artifact in artifacts if artifact.is_file()} == {
        "failing-111111111111.error.txt",
        "later-222222222222.stdout.log",
        "later-222222222222.stderr.log",
    }
    assert len(failing.calls) == 2
    assert len(later.calls) == 2


def test_preserves_naive_timestamps_for_log_collection(tmp_path: Path) -> None:
    capture = FailedTestLogCapture()
    container = FakeContainer("local-time", "abcdef1234567890")
    start = datetime.now(timezone.utc).astimezone().replace(tzinfo=None)

    capture.write(
        tmp_path / "artifacts",
        start,
        start + timedelta(seconds=1),
        [container],  # type: ignore[list-item]
    )

    assert all(
        call["since"] == start - timedelta(seconds=1) for call in container.calls
    )


def test_returns_false_when_no_artifact_file_can_be_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = FailedTestLogCapture()
    start = datetime.now(timezone.utc)

    def reject_write(_path: Path, _content: str) -> int:
        raise OSError("read-only filesystem")

    monkeypatch.setattr(Path, "write_text", reject_write)
    wrote_artifact = capture.write(
        tmp_path / "artifacts",
        start,
        start + timedelta(seconds=1),
        [FakeContainer("container", "abcdef1234567890")],  # type: ignore[list-item]
    )

    assert not wrote_artifact


def test_returns_false_when_there_are_no_containers(tmp_path: Path) -> None:
    capture = FailedTestLogCapture()
    start = datetime.now(timezone.utc)

    wrote_artifact = capture.write(
        tmp_path / "artifacts", start, start + timedelta(seconds=1), []
    )

    assert not wrote_artifact
    assert list(tmp_path.iterdir()) == []
