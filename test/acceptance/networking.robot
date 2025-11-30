*** Settings ***
Documentation       Showcasing how to connect multiple containers over a Docker network

Library             TestcontainersLibrary


*** Test Cases ***
Specify network directly when creating the container
    [Documentation]    You can pass a created network directly when creating a generic docker container.
    ...    Set a network alias if you want other networks to be able to communicate with it via hostname.
    ...    Created networks are automatically cleaned up in the end_test / end_suite hooks, just as the
    ...    the containers themselves.
    # First we create the network
    ${network}=    Create Network

    # Next, we create a container running a simple server, and pass in the network.
    # Additionally, we specify under which alias(es) the server should be reachable on this network.
    ${server}=    Create Docker Container
    ...    image=traefik/whoami
    ...    ports=[80]
    ...    network=${network}
    ...    network_aliases=["server"]
    Wait For Http Endpoint    container=${server}    port=80    path=/api    status_code=200

    # Create a second container on the same network and check if we can connect to the server.
    ${client}=    Create Docker Container
    ...    image=curlimages/curl:latest
    ...    network=${network}
    ...    command=http://server/api
    # Wait a bit, because sometimes testcontainers gets confused if
    # the container is a one-off container that directly exits.
    Sleep    0.5s
    Wait For Log Message    ${client}    hostname

Connecting containers after they were created
    [Documentation]    Containers can also be connected to a network after they are created.
    ...    This can be especially useful for container types that do not support directly passing in
    ...    the network when creating the container.
    # ServerContainer does not support the `network` parameter, therefore we need to connect it afterwards.
    ${server}=    Create Server Container    image=traefik/whoami    port=80

    # Create the network and then connect the container to it
    ${network}=    Create Network
    Connect Container To Network    ${server}    ${network}    aliases=["server"]

    # Create a client container and verify we can connect to the server.
    ${client}=    Create Docker Container
    ...    image=curlimages/curl:latest
    ...    network=${network}
    ...    command=http://server/api
    # Wait a bit, because sometimes testcontainers gets confused if
    # the container is a one-off container that directly exits.
    Sleep    0.5s
    Wait For Log Message    ${client}    hostname
