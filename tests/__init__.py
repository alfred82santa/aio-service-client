from asyncio import Future, create_task, get_event_loop

from aiohttp import ClientResponse, RequestInfo
from aiohttp.helpers import TimerContext
from yarl import URL


async def create_fake_response(method, url, *, session, headers=None, loop=None):
    loop = loop or get_event_loop()

    async def writer(*args, **kwargs):
        return None

    continue100 = Future()
    continue100.set_result(False)

    return ClientResponse(method, URL(url),
                          writer=create_task(writer()),
                          continue100=continue100,
                          timer=TimerContext(loop=loop),
                          request_info=RequestInfo(URL(url),
                                                   method,
                                                   headers or []),
                          traces=[],
                          loop=loop,
                          session=session)
