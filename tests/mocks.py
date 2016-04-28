from aiohttp.client_reqrep import ClientResponse
from asyncio.events import get_event_loop


class FakeMock:

    def __init__(self, mock_desc, loop=None):
        self.mock_desc = mock_desc
        self.loop = loop or get_event_loop()

    def __call__(self, *args, **kwargs):
        args = list(args)
        try:
            method = kwargs['method']
        except KeyError:
            method = args.pop()

        try:
            url = kwargs['url']
        except KeyError:
            url = args.pop()

        response = ClientResponse(method, url)
        response._post_init(self.loop)
        response.status = 200

        return response
