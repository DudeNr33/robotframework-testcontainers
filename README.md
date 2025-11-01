# robotframework-testcontainers

Robot Framework keywords for [testcontainers](https://github.com/testcontainers/testcontainers-python).

## Installation

- using `pip`:

```shell
pip install robotframework-testcontainers
```

- using `uv`:

```shell
uv add robotframework-testcontainers
```

- using `poetry`:

```shell
poetry add robotframework-testcontainers
```

## Usage

Starting a container can be done with a single keyword:

```robot
*** Settings ***
Library    TestcontainersLibrary

*** Test Cases ***
Basic Usage Example
    Create Docker Container    image=hello-world
```

`TestcontainersLibrary` keeps track of all created containers.
It will take care of stopping all created containers at the end of the test,
by making use of the `end_test`/`end_suite` listener methods.

If you require more control, you can also manually start and stop
the container. Additionally, you can use different wait strategies
to wait for the container to be ready:

```robot
*** Settings ***
Library    TestcontainersLibrary

*** Test Cases ***
Advanced Usage with more control
    ${container}=    Create Docker Container    image=traefik/whoami    start=False    ports=[80]
    Start Container    ${container}
    Wait For Http Endpoint    ${container}    port=80    path=/api
    Stop Container    ${container}
```

You can also use any of the community maintained containers.
Be aware that you have to make sure to install the required dependencies
yourself.  
For example: starting a CockroachDB container requires installing `testcontainers[cockroachdb]`.
Use the `Create Community Container` keyword and specify which class to import from which module.
Any additional arguments can be passed in as keyword arguments.

```robot
*** Settings ***
Library             TestcontainersLibrary


*** Test Cases ***
Starting an CockroachDb Container
    ${password}=    Evaluate    str(uuid.uuid4())
    ${container}=    Create Community Container
    ...    module=testcontainers.cockroachdb
    ...    container_class=CockroachDBContainer
    ...    username=demoUser
    ...    password=${password}
    Log    ${container.get_connection_url()}
```

You can read the acceptance tests in `test/acceptance/` for more concrete usage examples.

## License

This project is licensed under the [MIT License](LICENSE).

### Third-Party Licenses

This library depends on the
[`testcontainers-python`](https://github.com/testcontainers/testcontainers-python)
package, which is licensed under the
[Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

No parts of `testcontainers-python` are copied or modified in this project.
It is used only as a dependency.
