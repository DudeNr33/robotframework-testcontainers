*** Settings ***
Documentation       Usage examples for ServerContainer

Library             TestcontainersLibrary
Library             RequestsLibrary


*** Test Cases ***
Usage Example of ServerContainer
    [Documentation]    For web servers, the `ServerContainer` testcontainer can be used.
    ${container}=    Create Server Container    port=80    image=traefik/whoami
    GET    http://localhost:${container.get_exposed_port(80)}/api
