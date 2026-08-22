*** Settings ***
Library     TestcontainersLibrary
Library     resources/fake_container.py


*** Test Cases ***
Get Container Logs returns decoded stdout by default
    [Documentation]    Retrieves stdout when no stream is specified and replaces malformed UTF-8 bytes.
    ${container}=    Create Fake Container
    ${logs}=    Get Container Logs    ${container}
    Should Be Equal    ${logs}    stdout �

Get Container Logs returns selected stderr
    [Documentation]    Retrieves stderr without including stdout when stream is set to stderr.
    ${container}=    Create Fake Container
    ${logs}=    Get Container Logs    ${container}    stream=stderr
    Should Be Equal    ${logs}    stderr only

Get Container Logs forwards assertions before named stream arguments
    [Documentation]    Sends positional assertion arguments to Assertion Engine before selecting stderr.
    ${container}=    Create Fake Container
    Get Container Logs    ${container}    contains    only    stream=stderr
