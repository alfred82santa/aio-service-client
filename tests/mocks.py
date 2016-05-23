from asyncio import coroutine

from service_client.mocks import BaseMock


class FakeMock(BaseMock):

    @coroutine
    def prepare_response(self):
        pass
