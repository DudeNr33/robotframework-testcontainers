class FakeContainer:
    def get_wrapped_container(self):
        return self

    def logs(self, stdout=True, stderr=True):
        if stderr is False:
            return b"stdout \xff"
        if stdout is False:
            return b"stderr only"
        return b"stdout \xffstderr only"


def create_fake_container():
    return FakeContainer()
