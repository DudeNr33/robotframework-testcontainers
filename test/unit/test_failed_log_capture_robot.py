from pathlib import Path

from robot import run  # type: ignore[attr-defined]


def test_failed_robot_tests_write_only_their_container_logs(tmp_path: Path) -> None:
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
    artifacts = tmp_path / "artifacts"
    suite = tmp_path / "capture.robot"
    suite.write_text(
        f"""
*** Settings ***
Library    TestcontainersLibrary    failure_logs_dir={artifacts}
Library    fake_container.py
Suite Setup    Start shared container

*** Test Cases ***
Captures failure
    ${{container}}=    Create Fake Container
    Start Container    ${{container}}
    Fail    expected failure

Skipped test
    ${{container}}=    Create Fake Container
    Start Container    ${{container}}
    Skip    expected skip

Expected failure
    ${{container}}=    Create Fake Container
    Start Container    ${{container}}
    Run Keyword And Expect Error    *    Fail    expected failure

Stopped container failure
    ${{container}}=    Create Fake Container
    Start Container    ${{container}}
    Stop Container    ${{container}}
    Fail    expected failure

*** Keywords ***
Start shared container
    ${{container}}=    Create Fake Container
    Start Container    ${{container}}
""".strip()
    )

    assert (
        run(str(suite), outputdir=str(tmp_path / "output"), pythonpath=[str(resources)])
        == 2
    )

    logs = list(artifacts.glob("**/*.log"))
    assert {log.name for log in logs} == {
        "web-api-2-000000000000.stdout.log",
        "web-api-2-000000000000.stderr.log",
    }
    assert {log.read_text() for log in logs} == {"stdout", "stderr"}
