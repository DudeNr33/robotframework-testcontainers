import importlib
from typing import Any
from pathlib import Path
from robot.api.deco import library, keyword
from robot.api import logger
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy, HttpWaitStrategy
from testcontainers.generic.server import ServerContainer


@library(listener="SELF")
class TestcontainersLibrary:
    """
    Keywords for [https://testcontainers.com/|Testcontainers].
    """

    def __init__(self) -> None:
        self._containers: list[DockerContainer] = []

    @keyword
    def create_docker_container(
        self,
        image: str,
        command: str | None = None,
        env: dict[str, str] | None = None,
        name: str | None = None,
        ports: list[int] | None = None,
        volumes: list[tuple[Path, str, str]] | None = None,
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
        container = clazz(**kwargs)
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
        try:
            container.start()
            self._containers.append(container)
            return container
        except Exception:
            container.stop()
            raise

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
        The library instance will take care of stopping all containers it has
        started during it's lifecycle via listener methods.
        """
        self._containers.remove(container)
        container.stop()

    def _end_test(self, name: Any, attrs: Any) -> None:
        for container in self._containers.copy():
            cname = container.get_wrapped_container().name
            logger.console(
                f"\n\tTestcontainersLibrary: stopping container {cname} in end_test hook."
            )
            self.stop_container(container)

    def _end_suite(self, name: Any, attrs: Any) -> None:
        for container in self._containers.copy():
            cname = container.get_wrapped_container().name
            logger.console(
                f"\n\tTestcontainersLibrary: stopping container {cname} in end_suite hook."
            )
            self.stop_container(container)
