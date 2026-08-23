class FakeContainer:
    name = "fake-container"

    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def get_wrapped_container(self) -> "FakeContainer":
        return self


last_container: FakeContainer | None = None


def create_lifecycle_fake_container() -> FakeContainer:
    global last_container
    last_container = FakeContainer()
    return last_container


def lifecycle_fake_container_should_be_stopped() -> None:
    assert last_container is not None
    assert last_container.started
    assert last_container.stopped
