*** Settings ***
Library     DateTime
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

Get Container Logs passes naive datetime bounds to Docker
    [Documentation]    Robot converts DateTime values before the library passes them to Docker unchanged.
    ${container}=    Create Fake Container
    ${since}=    Get Current Date    increment=-10s    result_format=datetime
    ${until}=    Get Current Date    result_format=datetime
    Get Container Logs    ${container}    contains    stdout    since=${since}    until=${until}
    Log Filters Should Match    ${container}    ${since}    ${until}

Get Container Logs preserves timezone-aware datetime offsets
    [Documentation]    Docker receives the timezone-aware datetime rather than a normalized replacement.
    ${container}=    Create Fake Container
    VAR    ${since}=    2025-01-02 03:04:05+05:30
    Get Container Logs    ${container}    since=${since}
    Log Filter Should Preserve Offset    ${container}    ${since}

Get Container Logs includes Docker timestamps on request
    [Documentation]    Docker timestamps appear in the decoded selected stream only when requested.
    ${container}=    Create Fake Container
    ${logs}=    Get Container Logs    ${container}    stream=stderr    timestamps=${True}
    Should Contain    ${logs}    2025-01-01T00:00:00.000000000Z stderr only

Get Container Logs accepts all log options with Docker
    [Documentation]    Retrieves bounded, timestamped stdout from a real hello-world container.
    ${since}=    Get Current Date    increment=-1 minute    result_format=datetime
    ${container}=    Create Docker Container    image=hello-world
    Wait For Log Message    ${container}    Hello from Docker!
    ${until}=    Get Current Date    increment=1 minute    result_format=datetime
    ${logs}=    Get Container Logs    ${container}    contains    Hello from Docker!    stream=stdout    since=${since}    until=${until}    timestamps=${True}
    Should Match Regexp    ${logs}    (?s)^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*Hello from Docker!
