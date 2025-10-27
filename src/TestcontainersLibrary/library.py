from pathlib import Path
from robot.api.deco import library, keyword
from robot.api import logger
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy, HttpWaitStrategy
from testcontainers.generic.server import ServerContainer


@library(listener="SELF")
class TestcontainersLibrary:
    def __init__(self):
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
        container = ServerContainer(port=port, image=image)
        if start:
            self.start_container(container)
        return container

    @keyword
    def bind_ports(
        self, container: DockerContainer, container_port: int, host_port: int
    ) -> DockerContainer:
        container.with_bind_ports(container_port, host_port)
        return container

    @keyword
    def start_container(self, container: DockerContainer) -> DockerContainer:
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
        LogMessageWaitStrategy(message, times).wait_until_ready(container)

    @keyword
    def wait_for_http_endpoint(
        self, container: DockerContainer, port: int, path: str
    ) -> None:
        HttpWaitStrategy(port, path).wait_until_ready(container)

    @keyword
    def stop_container(self, container: DockerContainer) -> None:
        self._containers.remove(container)
        container.stop()

    def _end_test(self, name, attrs) -> None:
        for container in self._containers.copy():
            cname = container.get_wrapped_container().name
            logger.console(
                f"\n\tTestcontainersLibrary: stopping container {cname} in end_test hook."
            )
            self.stop_container(container)

    def _end_suite(self, name, attrs) -> None:
        for container in self._containers.copy():
            cname = container.get_wrapped_container().name
            logger.console(
                f"\n\tTestcontainersLibrary: stopping container {cname} in end_suite hook."
            )
            self.stop_container(container)
