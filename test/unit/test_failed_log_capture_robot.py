from pathlib import Path

import pytest
from robot import run  # type: ignore[attr-defined]


def test_failed_robot_tests_capture_all_active_container_logs(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    (resources / "fake_container.py").write_text(
        """
class FakeContainer:
    count = 0

    def __init__(self):
        type(self).count += 1
        self.name = f"web/api-{self.count}"
        self.id = f"{self.count:016d}"

    def start(self):
        pass

    def stop(self):
        pass

    def get_wrapped_container(self):
        return self

    def logs(self, stdout=True, **_):
        return b"stdout" if stdout else b"stderr"


def create_fake_container():
    return FakeContainer()
""".strip()
    )
    output = tmp_path / "output"
    artifacts = output / "container-logs"
    suite = tmp_path / "capture.robot"
    suite.write_text(
        """
*** Settings ***
Library    TestcontainersLibrary
Library    fake_container.py
Suite Setup    Start shared container

*** Test Cases ***
Captures failure
    ${container}=    Create Fake Container
    Start Container    ${container}
    Fail    expected failure

Stops suite setup container
    Stop Container    ${shared}

Skipped test
    ${container}=    Create Fake Container
    Start Container    ${container}
    Skip    expected skip

Expected failure
    ${container}=    Create Fake Container
    Start Container    ${container}
    Run Keyword And Expect Error    *    Fail    expected failure

Stopped container failure
    ${container}=    Create Fake Container
    Start Container    ${container}
    Stop Container    ${container}
    Fail    expected failure

*** Keywords ***
Start shared container
    ${container}=    Create Fake Container
    Start Container    ${container}
    Set Suite Variable    ${shared}    ${container}
""".strip()
    )

    assert (
        run(
            str(suite),
            outputdir=str(output),
            pythonpath=[str(resources)],
            listener="TestcontainersLibrary.FailedTestLogCollector",
        )
        == 2
    )

    logs = list(artifacts.glob("**/*.log"))
    assert {log.name for log in logs} == {
        "web_api-1-000000000000.stdout.log",
        "web_api-1-000000000000.stderr.log",
        "web_api-2-000000000000.stdout.log",
        "web_api-2-000000000000.stderr.log",
    }
    assert {log.read_text() for log in logs} == {"stdout", "stderr"}
    artifact_directories = {log.parent for log in logs}
    assert len(artifact_directories) == 1
    artifact_directory = artifact_directories.pop()
    assert artifact_directory.relative_to(artifacts).parts[1:] == (
        "Capture",
        "Captures_failure",
    )
    assert (output / "log.html").read_text().count(str(artifact_directory)) == 1


def test_listener_captures_root_suite_container_for_child_without_library_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helpers = tmp_path / "helpers"
    helpers.mkdir()
    (helpers / "fake_container.py").write_text(
        """
class FakeContainer:
    name = "root-container"
    id = "abcdef1234567890"

    def start(self):
        pass

    def stop(self):
        pass

    def get_wrapped_container(self):
        return self

    def logs(self, stdout=True, **_):
        return b"root stdout" if stdout else b"root stderr"


def create_fake_container():
    return FakeContainer()
""".strip()
    )
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    (root / "__init__.robot").write_text(
        """
*** Settings ***
Library    TestcontainersLibrary
Library    fake_container.py
Suite Setup    Start root container

*** Keywords ***
Start root container
    ${container}=    Create Fake Container
    Start Container    ${container}
""".strip()
    )
    (child / "tests.robot").write_text(
        """
*** Test Cases ***
Child failure
    Fail    expected failure
""".strip()
    )
    artifacts = tmp_path / "artifacts"
    monkeypatch.chdir(tmp_path)

    assert (
        run(
            str(root),
            outputdir=str(tmp_path / "output"),
            pythonpath=[str(helpers)],
            listener="TestcontainersLibrary.FailedTestLogCollector:artifacts",
        )
        == 1
    )

    logs = list(artifacts.glob("**/*.log"))
    assert {log.name for log in logs} == {
        "root-container-abcdef123456.stdout.log",
        "root-container-abcdef123456.stderr.log",
    }
    assert {log.read_text() for log in logs} == {"root stdout", "root stderr"}
    assert logs[0].parent.relative_to(artifacts).parts[1:] == (
        "Root",
        "Child",
        "Tests",
        "Child_failure",
    )


def test_failed_robot_test_without_active_containers_does_not_log_artifact_path(
    tmp_path: Path,
) -> None:
    suite = tmp_path / "failing.robot"
    suite.write_text(
        """
*** Test Cases ***
Fails
    Fail    expected failure
""".strip()
    )
    artifacts = tmp_path / "artifacts"
    output = tmp_path / "output"

    assert (
        run(
            str(suite),
            outputdir=str(output),
            listener=f"TestcontainersLibrary.FailedTestLogCollector:{artifacts}",
        )
        == 1
    )
    assert not artifacts.exists()
    assert str(artifacts) not in (output / "log.html").read_text()


def test_passing_robot_test_does_not_create_artifact_root(tmp_path: Path) -> None:
    suite = tmp_path / "passing.robot"
    suite.write_text(
        """
*** Test Cases ***
Passes
    No Operation
""".strip()
    )
    artifacts = tmp_path / "artifacts"

    assert (
        run(
            str(suite),
            outputdir=str(tmp_path / "output"),
            listener=f"TestcontainersLibrary.FailedTestLogCollector:{artifacts}",
        )
        == 0
    )
    assert not artifacts.exists()


def test_library_import_rejects_removed_failure_logs_argument(tmp_path: Path) -> None:
    suite = tmp_path / "removed_argument.robot"
    suite.write_text(
        """
*** Settings ***
Library    TestcontainersLibrary    failure_logs_dir=artifacts

*** Test Cases ***
Cannot run
    Get Container Logs    missing
""".strip()
    )

    assert run(str(suite), outputdir=str(tmp_path / "output")) == 1
