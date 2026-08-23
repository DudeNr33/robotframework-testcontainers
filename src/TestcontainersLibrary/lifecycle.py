from typing import Literal

from robot.api import logger
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network


class ResourceLifecycle:
    """Track and clean up containers and networks started by one library instance."""

    def __init__(self) -> None:
        self._containers: list[DockerContainer] = []
        self._networks: list[Network] = []

    def start_container(self, container: DockerContainer) -> DockerContainer:
        try:
            container.start()
            self._containers.append(container)
            return container
        except Exception:
            container.stop()
            raise

    def stop_container(self, container: DockerContainer) -> None:
        self._containers.remove(container)
        container.stop()

    def create_network(self) -> Network:
        network = Network()
        network.create()
        self._networks.append(network)
        return network

    def remove_network(self, network: Network) -> None:
        self._networks.remove(network)
        network.remove()

    def cleanup(self, hook: Literal["end_test", "end_suite"]) -> None:
        for container in self._containers.copy():
            name = container.get_wrapped_container().name
            logger.console(
                f"\n\tTestcontainersLibrary: stopping container {name} in {hook} hook."
            )
            self.stop_container(container)
        for network in self._networks.copy():
            logger.console(
                f"\n\tTestcontainersLibrary: removing network {network.id} in {hook} hook."
            )
            self.remove_network(network)
