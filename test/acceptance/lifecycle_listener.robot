*** Settings ***
Library     TestcontainersLibrary
Library     resources/fake_lifecycle.py


*** Test Cases ***
Listener cleans up containers started by keywords
    ${container}=    Create Lifecycle Fake Container
    Start Container    ${container}

Listener cleanup completed after the prior test
    Lifecycle Fake Container Should Be Stopped
