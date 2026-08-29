from pathlib import Path

from robot import run  # type: ignore[attr-defined]


def test_nested_suites_clean_resources_owned_by_each_lifecycle(tmp_path: Path) -> None:
    helpers = tmp_path / "helpers"
    helpers.mkdir()
    (helpers / "fake_resources.py").write_text(
        """
class FakeContainer:
    def __init__(self, name, stop_log):
        self.name = name
        self.stop_log = stop_log

    def start(self):
        pass

    def stop(self):
        with open(self.stop_log, "a") as output:
            output.write(f"{self.name}\\n")

    def get_wrapped_container(self):
        return self


def create_fake_container(name, stop_log):
    return FakeContainer(name, stop_log)
""".strip()
    )
    stop_log = tmp_path / "stops.txt"
    resource_file = tmp_path / "resources.robot"
    resource_file.write_text(
        """
*** Settings ***
Library    TestcontainersLibrary
Library    fake_resources.py

*** Keywords ***
Start Named Container
    [Arguments]    ${name}    ${stop_log}
    ${container}=    Create Fake Container    ${name}    ${stop_log}
    Start Container    ${container}
""".strip()
    )

    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    (root / "__init__.robot").write_text(
        f"""
*** Settings ***
Resource    {resource_file}
Suite Setup    Start Named Container    root    {stop_log}
""".strip()
    )
    (child / "__init__.robot").write_text(
        f"""
*** Settings ***
Resource    {resource_file}
Suite Setup    Start Named Container    child    {stop_log}
""".strip()
    )
    (child / "tests.robot").write_text(
        f"""
*** Settings ***
Resource    {resource_file}

*** Test Cases ***
Owns test resource
    Start Named Container    test    {stop_log}
""".strip()
    )

    assert (
        run(str(root), outputdir=str(tmp_path / "output"), pythonpath=[str(helpers)])
        == 0
    )
    assert stop_log.read_text().splitlines() == ["test", "child", "root"]
