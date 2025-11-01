*** Settings ***
Documentation       Community containers can be used as long as the required
...                 package is installed in the Python environment.

Library             TestcontainersLibrary


*** Test Cases ***
Starting a Redis Container
    [Documentation]    Simple example for starting a Redis Container.
    ${container}=    Create Community Container
    ...    module=testcontainers.redis
    ...    container_class=RedisContainer
    Log    ${container.get_exposed_port(6379)}

Starting an CockroachDb Container
    [Documentation]    Any custom arguments for the container can be
    ...    passed as keyword arguments to the library keyword. However,
    ...    no type conversion is performed.
    ${password}=    Evaluate    str(uuid.uuid4())
    ${container}=    Create Community Container
    ...    module=testcontainers.cockroachdb
    ...    container_class=CockroachDBContainer
    ...    username=demoUser
    ...    password=${password}
    Should Contain    ${container.get_connection_url()}    demoUser:${password}@localhost
    Log    ${container.get_connection_url()}
