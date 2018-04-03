import logging
from asyncio import wait_for, TimeoutError
from datetime import datetime
from urllib.parse import quote_plus

import weakref
from async_timeout import timeout as TimeoutContext
from functools import wraps
from multidict import CIMultiDict

from service_client.utils import IncompleteFormatter, random_token


class BasePlugin:

    def assign_service_client(self, service_client):
        self.service_client = service_client

    @property
    def service_client(self):
        return self._service_client()

    @service_client.setter
    def service_client(self, service_client):
        self._service_client = weakref.ref(service_client)


class PathTokens(BasePlugin):

    def __init__(self, default_tokens=None):
        self.default_token = default_tokens or {}

    async def prepare_path(self, endpoint_desc, session, request_params, path):
        tokens = self.default_token.copy()
        try:
            tokens.update(endpoint_desc['path_tokens'])
        except KeyError:
            pass
        tokens.update(request_params)
        formatter = IncompleteFormatter()
        ret = formatter.format(path, **{k: quote_plus(str(v)) for k, v in tokens.items()})
        for field in formatter.get_substituted_fields():
            try:
                request_params.pop(field)
            except KeyError:
                pass
        return ret


class Headers(BasePlugin):

    def __init__(self, default_headers=None):
        self.default_headers = default_headers.copy() if default_headers else {}

    async def prepare_request_params(self, endpoint_desc, session, request_params):
        headers = CIMultiDict()
        headers.update(self.default_headers)
        headers.update(endpoint_desc.get('headers', {}))
        headers.update(request_params.get('headers', {}))
        request_params['headers'] = headers


class Timeout(BasePlugin):

    def __init__(self, default_timeout=None):
        self.default_timeout = default_timeout

    async def before_request(self, endpoint_desc, session, request_params):
        try:
            timeout = request_params.pop('timeout')
        except KeyError:
            timeout = endpoint_desc.get('timeout', self.default_timeout)

        if timeout is None:
            return

        def decorator(func):
            @wraps(func)
            async def request_wrapper(*args, **kwargs):
                with TimeoutContext(timeout=timeout):
                    return (await func(*args, **kwargs))

            return request_wrapper

        session.decorate_attr('request', decorator)
        session.timeout = timeout


class Elapsed(BasePlugin):

    def __init__(self, headers=True, read=True, parse=True):
        self.headers = headers
        self.read = read
        self.parse = parse

    def _elapsed_enabled(self, elapsed_type, endpoint_desc, session, request_params):
        result = getattr(self, elapsed_type)
        try:
            result = endpoint_desc['elapsed'][elapsed_type]
        except KeyError:
            pass

        try:
            result = request_params.pop(elapsed_type + "_elapsed")
        except KeyError:
            pass

        return result

    def prepare_response(self, endpoint_desc, session, request_params, response):

        def decorator(func):
            @wraps(func)
            async def start_wrapper(*args, **kwargs):
                response.start_headers = datetime.now()
                r = await func(*args, **kwargs)
                response.headers_elapsed = datetime.now() - response.start_headers
                return r

            return start_wrapper

        if self._elapsed_enabled('headers', endpoint_desc, session, request_params):
            response.decorate_attr('start', decorator)

    async def on_response(self, endpoint_desc, session, request_params, response):
        if self._elapsed_enabled('read', endpoint_desc, session, request_params):
            response.start_read = datetime.now()

    async def on_read(self, endpoint_desc, session, request_params, response):
        try:
            response.read_elapsed = datetime.now() - response.start_read
        except AttributeError:
            pass

        if self._elapsed_enabled('parse', endpoint_desc, session, request_params):
            response.start_parse = datetime.now()

    async def on_parsed_response(self, endpoint_desc, session, request_params, response):
        try:
            response.parse_elapsed = datetime.now() - response.start_parse
        except AttributeError:
            pass


class TrackingToken(BasePlugin):

    def __init__(self, prefix='', length=10):
        self.prefix = prefix
        self.length = length

    async def prepare_session(self, endpoint_desc, session, request_params):
        try:
            tracking_token = request_params.pop('tracking_token')
        except KeyError:
            tracking_token = random_token(self.length)

        try:
            prefix = request_params.pop('tracking_token_prefix')
        except KeyError:
            prefix = self.prefix

        session.tracking_token = prefix + tracking_token

    async def on_response(self, endpoint_desc, session, request_params, response):
        response.tracking_token = session.tracking_token


class QueryParams(BasePlugin):

    def __init__(self, default_query_params=None):
        self.default_query_params = default_query_params

    async def prepare_request_params(self, endpoint_desc, session, request_params):
        try:
            query_params = self.default_query_params.copy()
        except AttributeError:
            query_params = {}
        query_params.update(endpoint_desc.get('query_params', {}))
        query_params.update(request_params.get('params', {}))
        request_params['params'] = {k: v for k, v in query_params.items() if v is not None}


class BaseLogger(BasePlugin):

    def __init__(self, logger, max_body_length=0, level=logging.INFO,
                 on_exception_level=logging.CRITICAL,
                 on_parse_exception_level=logging.CRITICAL):
        self.logger = logger
        self.max_body_length = max_body_length
        self.level = level
        self.on_exception_level = on_exception_level
        self.on_parse_exception_level = on_parse_exception_level

    def _prepare_body(self, body_string):
        return body_string[:self.max_body_length]

    def _prepare_record(self, endpoint_desc, session, request_params):
        log_data = {'endpoint': endpoint_desc['endpoint'],
                    'service_name': self.service_client.name}

        log_data.update(session.get_wrapper_data())
        log_data.update(request_params)

        return log_data

    async def _prepare_request_log_record(self, endpoint_desc, session, request_params):
        log_data = self._prepare_record(endpoint_desc, session, request_params)
        log_data['action'] = 'REQUEST'
        return log_data

    async def _prepare_response_log_record(self, endpoint_desc, session, request_params, response):
        log_data = self._prepare_record(endpoint_desc, session, request_params)
        log_data['action'] = 'RESPONSE'
        log_data['status_code'] = response.status
        log_data['headers'] = response.headers

        log_data.update(response.get_wrapper_data())
        try:
            del log_data['data']
        except KeyError:  # pragma: no cover
            pass

        if endpoint_desc.get('logger', {}).get('hidden_response_body', False):
            log_data['body'] = '<HIDDEN>'
        elif endpoint_desc.get('stream_response', False):
            log_data['body'] = '<STREAM>'
        else:
            try:
                log_data['body'] = self._prepare_body(response.data)
            except AttributeError:
                log_data['body'] = self._prepare_body((await response.text()))

        return log_data

    def _prepare_exception(self, log_data, ex):
        log_data['action'] = 'EXCEPTION'
        log_data['exception'] = ex

    async def _prepare_parse_response_exception_log_record(self, endpoint_desc, session, request_params, response, ex):
        log_data = await self._prepare_response_log_record(endpoint_desc, session, request_params, response)
        self._prepare_exception(log_data, ex)

        return log_data

    async def _prepare_exception_log_record(self, endpoint_desc, session, request_params, ex):
        log_data = self._prepare_record(endpoint_desc, session, request_params)
        self._prepare_exception(log_data, ex)

        return log_data

    async def on_exception(self, endpoint_desc, session, request_params, ex):
        log_data = await self._prepare_exception_log_record(endpoint_desc, session, request_params, ex)
        self.logger.log(self.on_exception_level, str(ex), extra=log_data)

    async def on_parse_exception(self, endpoint_desc, session, request_params, response, ex):
        log_data = await self._prepare_parse_response_exception_log_record(endpoint_desc, session,
                                                                           request_params, response, ex)
        self.logger.log(self.on_parse_exception_level, str(ex), extra=log_data)


class InnerLogger(BaseLogger):
    async def _prepare_on_request_log_record(self, endpoint_desc, session, request_params):
        log_data = await self._prepare_request_log_record(endpoint_desc, session, request_params)

        if endpoint_desc.get('logger', {}).get('hidden_request_body', False):
            log_data['body'] = '<HIDDEN>'
        elif endpoint_desc.get('stream_request', False):
            log_data['body'] = '<STREAM>'
        else:
            try:
                log_data['body'] = self._prepare_body(log_data['data'])
                del log_data['data']
            except KeyError:
                log_data['body'] = '<NO BODY>'

        try:
            del log_data['data']
        except KeyError:
            pass

        return log_data

    async def before_request(self, endpoint_desc, session, request_params):
        log_data = await self._prepare_on_request_log_record(endpoint_desc, session, request_params)
        self.logger.log(self.level, "Sending request", extra=log_data)

    async def on_response(self, endpoint_desc, session, request_params, response):
        log_data = await self._prepare_response_log_record(endpoint_desc, session, request_params, response)
        self.logger.log(self.level, "Response received", extra=log_data)


class OuterLogger(BaseLogger):
    async def _prepare_prepare_payload_log_record(self, endpoint_desc, session, request_params, payload):
        log_data = await self._prepare_request_log_record(endpoint_desc, session, request_params)

        if endpoint_desc.get('logger', {}).get('hidden_request_body', False):
            log_data['body'] = '<HIDDEN>'
        elif endpoint_desc.get('stream_request', False):
            log_data['body'] = '<STREAM>'
        elif payload is not None:
            log_data['body'] = self._prepare_body(str(payload))
        else:
            log_data['body'] = '<NO BODY>'

        return log_data

    async def prepare_payload(self, endpoint_desc, session, request_params, payload):
        log_data = await self._prepare_prepare_payload_log_record(endpoint_desc, session,
                                                                  request_params, payload)
        self.logger.log(self.level, "Sending request", extra=log_data)

    async def on_parsed_response(self, endpoint_desc, session, request_params, response):
        log_data = await self._prepare_response_log_record(endpoint_desc, session, request_params, response)
        self.logger.log(self.level, "Response received", extra=log_data)


class RequestLimitError(Exception):
    pass


class TooManyRequestsPendingError(RequestLimitError):
    pass


class TooMuchTimePendingError(RequestLimitError):
    pass


class BaseLimitPlugin(BasePlugin):
    SESSION_ATTR_TIME_BLOCKED = 'blocked'

    TOO_MANY_REQ_PENDING_MSG = "Too many requests pending"
    TOO_MUCH_TIME_MSG = "Request blocked too much time"

    def __init__(self, limit=1, timeout=None, hard_limit=None):
        self.limit = limit
        self._counter = 0
        self._fut = None
        self._pending = 0
        self._timeout = timeout
        self._hard_limit = hard_limit

    @property
    def pending(self):
        return self._pending

    async def _acquire(self):

        timeout = self._timeout
        while True:
            if self._counter < self.limit:
                self._counter += 1
                break

            if self._hard_limit is not None and self._hard_limit < self.pending:
                raise TooManyRequestsPendingError(self.TOO_MANY_REQ_PENDING_MSG)

            if self._fut is None:
                self._fut = self.service_client.loop.create_future()
            self._pending += 1

            try:
                now = self.service_client.loop.time()
                await wait_for(self._fut, timeout=timeout, loop=self.service_client.loop)
                if timeout is not None:
                    timeout -= self.service_client.loop.time() - now
                    if timeout <= 0:
                        raise TimeoutError()
            except TimeoutError:
                raise TooMuchTimePendingError(self.TOO_MUCH_TIME_MSG)
            finally:
                self._pending -= 1

    def _release(self):
        self._counter -= 1
        if self._fut is not None:
            self._fut.set_result(None)

    async def before_request(self, endpoint_desc, session, request_params):
        start = self.service_client.loop.time()
        try:
            await self._acquire()
        finally:
            setattr(session,
                    self.SESSION_ATTR_TIME_BLOCKED,
                    self.service_client.loop.time() - start)

    def close(self):
        if self._fut is not None:
            from service_client import ConnectionClosedError
            self._fut.set_exception(ConnectionClosedError('Connection closed'))


class Pool(BaseLimitPlugin):
    SESSION_ATTR_TIME_BLOCKED = 'blocked_by_pool'

    TOO_MANY_REQ_PENDING_MSG = "Too many requests pending on pool"
    TOO_MUCH_TIME_MSG = "Request blocked too much time on pool"

    async def on_response(self, endpoint_desc, session, request_params, response):
        self._release()

    async def on_exception(self, endpoint_desc, session, request_params, ex):
        if not isinstance(ex, RequestLimitError):
            self._release()


class RateLimit(BaseLimitPlugin):
    SESSION_ATTR_TIME_BLOCKED = 'blocked_by_ratelimit'

    TOO_MANY_REQ_PENDING_MSG = "Too many requests pending by rate limit"
    TOO_MUCH_TIME_MSG = "Request blocked too much time by rate limit"

    def __init__(self, period=1, *args, **kwargs):
        super(RateLimit, self).__init__(*args, **kwargs)
        self.period = period

    async def on_response(self, endpoint_desc, session, request_params, response):
        self.service_client.loop.call_later(self.period, self._release)

    async def on_exception(self, endpoint_desc, session, request_params, ex):
        if not isinstance(ex, RequestLimitError):
            self.service_client.loop.call_later(self.period, self._release)
