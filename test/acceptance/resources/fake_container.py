from datetime import datetime
from typing import Any


class FakeContainer:
    def __init__(self) -> None:
        self.log_options: dict[str, Any] = {}

    def get_wrapped_container(self) -> "FakeContainer":
        return self

    def logs(
        self,
        stdout: bool = True,
        stderr: bool = True,
        since: datetime | None = None,
        until: datetime | None = None,
        timestamps: bool = False,
    ) -> bytes:
        self.log_options = {
            "stdout": stdout,
            "stderr": stderr,
            "since": since,
            "until": until,
            "timestamps": timestamps,
        }
        timestamp = b"2025-01-01T00:00:00.000000000Z " if timestamps else b""
        if stderr is False:
            return timestamp + b"stdout \xff"
        if stdout is False:
            return timestamp + b"stderr only"
        return timestamp + b"stdout \xffstderr only"


def create_fake_container() -> FakeContainer:
    return FakeContainer()


def log_filters_should_match(
    container: FakeContainer, since: datetime, until: datetime
) -> None:
    assert container.log_options["since"] == since
    assert container.log_options["until"] == until
    assert since.tzinfo is None
    assert until.tzinfo is None


def log_filter_should_preserve_offset(
    container: FakeContainer, since: datetime
) -> None:
    received_since = container.log_options["since"]
    assert received_since == since
    assert received_since.utcoffset() == since.utcoffset()
