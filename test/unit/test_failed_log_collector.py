from pathlib import Path

import pytest

from TestcontainersLibrary import FailedTestLogCollector


def test_rejects_empty_artifact_root() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        FailedTestLogCollector("")


def test_rejects_artifact_root_that_is_a_file(tmp_path: Path) -> None:
    artifact_file = tmp_path / "artifacts"
    artifact_file.touch()

    with pytest.raises(ValueError, match="is not a directory"):
        FailedTestLogCollector(str(artifact_file))
