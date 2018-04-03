from asyncio import get_event_loop

from aiohttp import ClientResponse, RequestInfo
from yarl import URL


async def create_fake_response(method, url, *, session, headers=None, loop=None):
    return ClientResponse(method, URL(url),
                          writer=None, continue100=False, timer=None,
                          request_info=RequestInfo(URL(url), method,
                                                   headers or []),
                          auto_decompress=False,
                          traces=[], loop=loop or get_event_loop(), session=session)
