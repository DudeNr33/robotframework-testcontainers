import importlib
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from assertionengine import AssertionOperator, verify_assertion
from robot.api.deco import keyword, library

# see https://github.com/testcontainers/testcontainers-python/blob/main/src/testcontainers/generic.py#L9
from testcontainers.community.generic import ServerContainer  # type: ignore[attr-defined]  # ruff: isort: skip
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import HttpWaitStrategy, LogMessageWaitStrategy

from TestcontainersLibrary.lifecycle import ResourceLifecycle
from TestcontainersLibrary.listener import LifecycleListener
from TestcontainersLibrary.log_capture import FailedTestLogCapture


@library
class TestcontainersLibrary:
    """
    Keywords for [https://testcontainers.com/|Testcontainers].
    """

    def __init__(self, failure_logs_dir: Path | None = None) -> None:
        """
        ``failure_logs_dir`` enables failed-test log artifacts under this
        directory. For a failed test, the library saves separate stdout and
        stderr files for every active container started through the library.
        The files contain raw logs and may contain secrets.
        """
        failed_log_capture = (
            FailedTestLogCapture(failure_logs_dir)
            if failure_logs_dir is not None
            else None
        )
        self._resources = ResourceLifecycle.for_execution()
        self.ROBOT_LIBRARY_LISTENER = LifecycleListener(
            self._resources, failed_log_capture
        )

    @keyword
    def create_docker_container(
        self,
        image: str,
        command: str | None = None,
        env: dict[str, str] | None = None,
        name: str | None = None,
        ports: list[int] | None = None,
        volumes: list[tuple[Path, str, str]] | None = None,
        network: Network | None = None,
        network_aliases: list[str] | None = None,
        start: bool = True,
    ) -> DockerContainer:
        """
        Create a basic [https://testcontainers-python.readthedocs.io/en/latest/core/README.html#testcontainers.core.container.DockerContainer|DockerContainer].
        Returns the container instance.

        By default, the created container is started directly.

        This can be prevented by setting ``start=False``, e.g. if
        you need to customize the container before starting, like
        binding specific ports etc.
        In this case, use the ``Start Container`` keyword afterwards.
        """
        container = DockerContainer(
            image=image,
            command=command,
            env=env,
            name=name,
            ports=ports,
            volumes=self._resolve_volume_paths(volumes) if volumes else None,
            network=network,
            network_aliases=network_aliases,
        )
        if start:
            self.start_container(container)
        return container

    def _resolve_volume_paths(
        self, volumes: list[tuple[Path, str, str]]
    ) -> list[tuple[str, str, str]]:
        return [(v[0].resolve().as_posix(), v[1], v[2]) for v in volumes]

    @keyword
    def create_server_container(
        self, port: int, image: str, start: bool = True
    ) -> ServerContainer:
        """
        Create a [https://testcontainers-python.readthedocs.io/en/latest/modules/generic/README.html#testcontainers.generic.ServerContainer|ServerContainer]

        By default, the created container is started directly.

        This can be prevented by setting ``start=False``, e.g. if
        you need to customize the container before starting, like
        binding specific ports etc.
        In this case, use the ``Start Container`` keyword afterwards.
        """
        container = ServerContainer(port=port, image=image)
        if start:
            self.start_container(container)
        return container

    @keyword
    def create_community_container(
        self, module: str, container_class: str, start: bool = True, **kwargs: Any
    ) -> DockerContainer:
        """
        Create a [https://testcontainers-python.readthedocs.io/en/latest/modules/index.html|community maintained container].

        Specify the ``module`` and ``container_class`` the same way you would import
        it in Python.\nFor example, the ``RedisContainer`` that you would import via\n
        ``from testcontainers.redis import RedisContainer``
        \nin Python code can be created with\n
        ``| Create Community Container | module=testcontainers.redis | container_class=RedisContainer |``.\n
        Extra arguments required by the container can be passed as keyword arguments.

        By default, the created container is started directly.

        This can be prevented by setting ``start=False``, e.g. if
        you need to customize the container before starting, like
        binding specific ports etc.
        In this case, use the ``Start Container`` keyword afterwards.
        """
        _module = importlib.import_module(module)
        clazz = getattr(_module, container_class)
        container = cast(DockerContainer, clazz(**kwargs))
        if start:
            self.start_container(container)
        return container

    @keyword
    def bind_ports(
        self, container: DockerContainer, container_port: int, host_port: int
    ) -> DockerContainer:
        """
        Bind a container port to a host port.
        """
        container.with_bind_ports(container_port, host_port)
        return container

    @keyword
    def start_container(self, container: DockerContainer) -> DockerContainer:
        """
        Start the given container.
        """
        return self._resources.start_container(container)

    @keyword
    def get_container_logs(
        self,
        container: DockerContainer,
        assertion_operator: AssertionOperator | None = None,
        assertion_expected: Any = None,
        message: str = "",
        custom_message: str | None = None,
        stream: Literal["stdout", "stderr"] = "stdout",
        since: datetime | None = None,
        until: datetime | None = None,
        timestamps: bool = False,
    ) -> str:
        """
        Return a managed container's stdout or stderr.

        Stdout is selected by default. Set ``stream=stderr`` to retrieve stderr.
        Pass absolute datetimes with ``since`` and ``until`` to bound the logs.
        Set ``timestamps=True`` to include Docker timestamps in each line. Pass
        assertion-engine arguments after the container to assert against the selected
        container log.

        Examples:
        | ${stderr}= | Get Container Logs | ${container} | stream=stderr |         |
        |            | Get Container Logs | ${container} | contains      | started |
        | ${logs}=   | Get Container Logs | ${container} | since=${start} | timestamps=${True} |
        """
        wrapped_container = container.get_wrapped_container()

        stdout = stream == "stdout"
        stderr = stream == "stderr"
        log_bytes = wrapped_container.logs(
            stdout=stdout,
            stderr=stderr,
            since=since,
            until=until,
            timestamps=timestamps,
        )

        container_log = log_bytes.decode("utf-8", errors="replace")
        return cast(
            str,
            verify_assertion(
                container_log,
                assertion_operator,
                assertion_expected,
                message,
                custom_message,
            ),
        )

    @keyword
    def wait_for_log_message(
        self, container: DockerContainer, message: str, times: int = 1
    ) -> None:
        """
        Wait until the given container has emitted the specified log message.
        The message can be a simple string or a regular expression.

        The container must already be started when calling this keyword.
        """
        LogMessageWaitStrategy(message, times).wait_until_ready(container)

    @keyword
    def wait_for_http_endpoint(
        self, container: DockerContainer, port: int, path: str, status_code: int = 200
    ) -> None:
        """
        Wait until the specified endpoint is reachable on the given container.

        The container must already be started when calling this keyword.
        """
        HttpWaitStrategy(port, path).for_status_code(status_code).wait_until_ready(
            container
        )

    @keyword
    def stop_container(self, container: DockerContainer) -> None:
        """
        Stop the given container.

        It is not required to call this keyword manually just to clean up after tests.
        The library stops containers automatically when the Robot test or suite
        that started them ends.
        """
        self._resources.stop_container(container)

    @keyword
    def create_network(self) -> Network:
        """
        Create a network to connect different containers with each other.

        Created networks are cleaned up when the Robot test or suite that created
        them ends.
        """
        return self._resources.create_network()

    @keyword
    def remove_network(self, network: Network) -> None:
        """
        Delete the given network.
        """
        self._resources.remove_network(network)

    @keyword
    def connect_container_to_network(
        self,
        container: DockerContainer,
        network: Network,
        aliases: list[str] | None = None,
    ) -> None:
        """
        Connect a container to a network. It will be reachable from other containers by its alias, if set.
        """
        container_id = container.get_wrapped_container().id
        if container_id is None:
            raise ValueError("Failed to obtain ID of wrapped container")
        network.connect(container_id=container_id, network_aliases=aliases)
