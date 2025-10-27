*** Settings ***
Documentation       Demonstrate and test the basic usage of plain DockerContainer testcontainers.

Library             TestcontainersLibrary
Library             RequestsLibrary

Suite Setup         Create Docker Container    image=hello-world


*** Test Cases ***
Create and directly start a container
    [Documentation]    Containers can be started and stopped via keywords.
    ${container}=    Create Docker Container    image=hello-world
    Wait For Log Message    container=${container}    message=Hello
    Stop Container    ${container}

Create a container and modify it before starting
    [Documentation]    By specifying `start=False`, the container will be created but not started.
    ...    This can be useful if the container should be modified further, e.g. for binding ports to
    ...    dedicated ports on the host.
    ${container}=    Create Docker Container    image=traefik/whoami    start=False
    ${container}=    Bind Ports    ${container}    container_port=80    host_port=8088
    Start Container    ${container}
    Wait For Http Endpoint    container=${container}    port=80    path=/api
    Stop Container    ${container}

Containers are cleaned up automatically
    [Documentation]    Containers do not need to be stopped manually inside the test or a teardown.
    ...    TestcontainersLibrary keeps track of all created containers and will stop them via
    ...    the end_test / end_suite listener methods.
    Create Docker Container    image=hello-world
    Log    This test does not explicitly stop the created container.
    Log    Watch the console output to see how it's cleaned up!

Access testcontainer methods
    [Documentation]    As the `Create Docker Container` keyword returns the `DockerContainer` instance,
    ...    any method not accessible via keywords can be called directly on the variable.
    ${container}=    Create Docker Container    image=traefik/whoami    start=False
    # Example: expose ports
    Start Container    ${container.with_exposed_ports(80)}
    VAR    ${exposed_port}=    ${container.get_exposed_port(80)}
    GET    http://localhost:${exposed_port}/api
