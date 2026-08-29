from dataclasses import dataclass
from typing import ClassVar, Literal, cast

from robot.api import logger
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

CleanupHook = Literal["end_test", "end_suite"]


@dataclass(frozen=True)
class ResourceOwner:
    kind: Literal["suite", "test"]
    longname: str


@dataclass
class ManagedResource:
    kind: Literal["container", "network"]
    resource: DockerContainer | Network
    owner: ResourceOwner | None


class ResourceLifecycle:
    """Track resources for one Robot execution and clean them by owner."""

    _execution: ClassVar["ResourceLifecycle | None"] = None

    def __init__(self) -> None:
        self._resources: list[ManagedResource] = []
        self._active_owner: ResourceOwner | None = None

    @classmethod
    def for_execution(cls) -> "ResourceLifecycle":
        if cls._execution is None:
            cls._execution = cls()
        return cls._execution

    def enter_suite(self, longname: str) -> None:
        self._active_owner = ResourceOwner("suite", longname)

    def enter_test(self, longname: str) -> None:
        self._active_owner = ResourceOwner("test", longname)

    def clear_owner(self) -> None:
        self._active_owner = None

    def start_container(self, container: DockerContainer) -> DockerContainer:
        owner = self._require_active_owner()
        try:
            container.start()
            self._resources.append(ManagedResource("container", container, owner))
            return container
        except Exception:
            container.stop()
            raise

    def stop_container(self, container: DockerContainer) -> None:
        container.stop()
        self._remove_resource(container)

    def active_containers(self) -> tuple[DockerContainer, ...]:
        return tuple(
            cast(DockerContainer, resource.resource)
            for resource in self._resources
            if resource.kind == "container"
        )

    def create_network(self) -> Network:
        owner = self._require_active_owner()
        network = Network()
        network.create()
        self._resources.append(ManagedResource("network", network, owner))
        return network

    def remove_network(self, network: Network) -> None:
        network.remove()
        self._remove_resource(network)

    def cleanup_test(self, longname: str) -> None:
        self._cleanup_owner(ResourceOwner("test", longname), "end_test")

    def cleanup_suite(self, longname: str) -> None:
        self._cleanup_owner(ResourceOwner("suite", longname), "end_suite")

    def cleanup(self, hook: CleanupHook) -> None:
        self._cleanup_resources(self._resources.copy(), hook)

    def _cleanup_owner(self, owner: ResourceOwner, hook: CleanupHook) -> None:
        self._cleanup_resources(
            [
                managed_resource
                for managed_resource in self._resources
                if managed_resource.owner == owner
            ],
            hook,
        )

    def _cleanup_resources(
        self,
        managed_resources: list[ManagedResource],
        hook: CleanupHook,
    ) -> None:
        first_error: Exception | None = None
        for kind in ("container", "network"):
            for managed_resource in managed_resources:
                if managed_resource.kind != kind:
                    continue
                try:
                    self._cleanup_resource(managed_resource, hook)
                except Exception as error:  # noqa: BLE001
                    logger.error(
                        f"TestcontainersLibrary: failed to clean up {kind}: {error}"
                    )
                    if first_error is None:
                        first_error = error
        if first_error is not None:
            raise first_error

    def _cleanup_resource(
        self, managed_resource: ManagedResource, hook: CleanupHook
    ) -> None:
        resource = managed_resource.resource
        if managed_resource.kind == "container":
            container = cast(DockerContainer, resource)
            name = container.get_wrapped_container().name
            logger.console(
                f"\n\tTestcontainersLibrary: stopping container {name} in {hook} hook."
            )
            self.stop_container(container)
        else:
            network = cast(Network, resource)
            logger.console(
                f"\n\tTestcontainersLibrary: removing network {network.id} in {hook} hook."
            )
            self.remove_network(network)

    def _require_active_owner(self) -> ResourceOwner:
        if self._active_owner is None:
            raise RuntimeError(
                "Containers and networks can only be started during Robot suite "
                "setup or test execution."
            )
        return self._active_owner

    def _remove_resource(self, resource: DockerContainer | Network) -> None:
        for managed_resource in self._resources:
            if managed_resource.resource is resource:
                self._resources.remove(managed_resource)
                return
        raise ValueError("Resource is not managed by this library execution.")
