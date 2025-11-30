*** Settings ***
Documentation       Showcasing how to connect multiple containers over a Docker network

Library             TestcontainersLibrary


*** Test Cases ***
Specify network directly when creating the container
    [Documentation]    You can pass a created network directly when creating a generic docker container.
    ...    Set a network alias if you want other networks to be able to communicate with it via hostname.
    ...    Created networks are automatically cleaned up in the end_test / end_suite hooks, just as the
    ...    the containers themselves.
    ${network}=    Create Network
    ${server}=    Create Docker Container
    ...    image=traefik/whoami
    ...    ports=[80]
    ...    network=${network}
    ...    network_aliases=["server"]
    Wait For Http Endpoint    container=${server}    port=80    path=/api    status_code=200
    ${client}=    Create Docker Container
    ...    image=nginx:stable
    ...    network=${network}
    ...    command=curl http://server/api
    Wait For Log Message    ${client}    hostname
    Log    ${client.get_logs()[0]}
