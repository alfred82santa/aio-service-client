import weakref
import logging
from asyncio import coroutine, Future
from functools import wraps
from datetime import datetime
from urllib.parse import quote_plus
from aiohttp.helpers import Timeout as TimeoutContext
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

    @coroutine
    def prepare_path(self, endpoint_desc, session, request_params, path):
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

    @coroutine
    def prepare_request_params(self, endpoint_desc, session, request_params):
        headers = request_params.get('headers', CIMultiDict()).copy()
        if not isinstance(headers, CIMultiDict):
            headers = CIMultiDict(headers)
        headers.update(self.default_headers)
        headers.update(endpoint_desc.get('headers', {}))
        headers.update(request_params.get('headers', {}))
        request_params['headers'] = headers


class Timeout(BasePlugin):

    def __init__(self, default_timeout=None):
        self.default_timeout = default_timeout

    @coroutine
    def before_request(self, endpoint_desc, session, request_params):
        try:
            timeout = request_params.pop('timeout')
        except KeyError:
            timeout = endpoint_desc.get('timeout', self.default_timeout)

        if timeout is None:
            return

        def decorator(func):
            @coroutine
            @wraps(func)
            def request_wrapper(*args, **kwargs):
                with TimeoutContext(timeout=timeout):
                    return (yield from func(*args, **kwargs))

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
            @coroutine
            @wraps(func)
            def start_wrapper(*args, **kwargs):
                response.start_headers = datetime.now()
                r = yield from func(*args, **kwargs)
                response.headers_elapsed = datetime.now() - response.start_headers
                return r

            return start_wrapper

        if self._elapsed_enabled('headers', endpoint_desc, session, request_params):
            response.decorate_attr('start', decorator)

    @coroutine
    def on_response(self, endpoint_desc, session, request_params, response):
        if self._elapsed_enabled('read', endpoint_desc, session, request_params):
            response.start_read = datetime.now()

    @coroutine
    def on_read(self, endpoint_desc, session, request_params, response):
        try:
            response.read_elapsed = datetime.now() - response.start_read
        except AttributeError:
            pass

        if self._elapsed_enabled('parse', endpoint_desc, session, request_params):
            response.start_parse = datetime.now()

    @coroutine
    def on_parsed_response(self, endpoint_desc, session, request_params, response):
        try:
            response.parse_elapsed = datetime.now() - response.start_parse
        except AttributeError:
            pass


class TrackingToken(BasePlugin):

    def __init__(self, prefix='', length=10):
        self.prefix = prefix
        self.length = length

    @coroutine
    def prepare_session(self, endpoint_desc, session, request_params):
        try:
            tracking_token = request_params.pop('tracking_token')
        except KeyError:
            tracking_token = random_token(self.length)

        try:
            prefix = request_params.pop('tracking_token_prefix')
        except KeyError:
            prefix = self.prefix

        session.tracking_token = prefix + tracking_token

    @coroutine
    def on_response(self, endpoint_desc, session, request_params, response):
        response.tracking_token = session.tracking_token


class QueryParams(BasePlugin):

    @coroutine
    def prepare_request_params(self, endpoint_desc, session, request_params):
        query_params = endpoint_desc.get('query_params', {}).copy()
        query_params.update(request_params.get('params', {}))
        request_params['params'] = query_params


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

    @coroutine
    def _prepare_request_log_record(self, endpoint_desc, session, request_params):
        log_data = self._prepare_record(endpoint_desc, session, request_params)
        log_data['action'] = 'REQUEST'
        return log_data

    @coroutine
    def _prepare_response_log_record(self, endpoint_desc, session, request_params, response):
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
                log_data['body'] = self._prepare_body((yield from response.text()))

        return log_data

    def _prepare_exception(self, log_data, ex):
        log_data['action'] = 'EXCEPTION'
        log_data['exception'] = ex

    @coroutine
    def _prepare_parse_response_exception_log_record(self, endpoint_desc, session, request_params, response, ex):
        log_data = yield from self._prepare_response_log_record(endpoint_desc, session, request_params, response)
        self._prepare_exception(log_data, ex)

        return log_data

    @coroutine
    def _prepare_exception_log_record(self, endpoint_desc, session, request_params, ex):
        log_data = self._prepare_record(endpoint_desc, session, request_params)
        self._prepare_exception(log_data, ex)

        return log_data

    @coroutine
    def on_exception(self, endpoint_desc, session, request_params, ex):
        log_data = yield from self._prepare_exception_log_record(endpoint_desc, session, request_params, ex)
        self.logger.log(self.on_exception_level, str(ex), extra=log_data)

    @coroutine
    def on_parse_exception(self, endpoint_desc, session, request_params, response, ex):
        log_data = yield from self._prepare_parse_response_exception_log_record(endpoint_desc, session,
                                                                                request_params, response, ex)
        self.logger.log(self.on_parse_exception_level, str(ex), extra=log_data)


class InnerLogger(BaseLogger):

    @coroutine
    def _prepare_on_request_log_record(self, endpoint_desc, session, request_params):
        log_data = yield from self._prepare_request_log_record(endpoint_desc, session, request_params)

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

    @coroutine
    def before_request(self, endpoint_desc, session, request_params):
        log_data = yield from self._prepare_on_request_log_record(endpoint_desc, session, request_params)
        self.logger.log(self.level, "Sending request", extra=log_data)

    @coroutine
    def on_response(self, endpoint_desc, session, request_params, response):
        log_data = yield from self._prepare_response_log_record(endpoint_desc, session, request_params, response)
        self.logger.log(self.level, "Response received", extra=log_data)


class OuterLogger(BaseLogger):

    @coroutine
    def _prepare_prepare_payload_log_record(self, endpoint_desc, session, request_params, payload):
        log_data = yield from self._prepare_request_log_record(endpoint_desc, session, request_params)

        if endpoint_desc.get('logger', {}).get('hidden_request_body', False):
            log_data['body'] = '<HIDDEN>'
        elif endpoint_desc.get('stream_request', False):
            log_data['body'] = '<STREAM>'
        elif payload is not None:
            log_data['body'] = self._prepare_body(str(payload))
        else:
            log_data['body'] = '<NO BODY>'

        return log_data

    @coroutine
    def prepare_payload(self, endpoint_desc, session, request_params, payload):
        log_data = yield from self._prepare_prepare_payload_log_record(endpoint_desc, session,
                                                                       request_params, payload)
        self.logger.log(self.level, "Sending request", extra=log_data)

    @coroutine
    def on_parsed_response(self, endpoint_desc, session, request_params, response):
        log_data = yield from self._prepare_response_log_record(endpoint_desc, session, request_params, response)
        self.logger.log(self.level, "Response received", extra=log_data)


class Pool(BasePlugin):

    def __init__(self, limit=1):
        self.limit = limit
        self._waiters = []
        self._acquired = 0

    def _acquire(self):
        self._acquired += 1

    def _release(self):
        self._acquired -= 1
        while self._acquired < self.limit:
            try:
                fut = self._waiters.pop()
                fut.set_result(None)
                self._acquire()
            except IndexError:  # pragma: no cover
                break

    @coroutine
    def before_request(self, endpoint_desc, session, request_params):
        if self._acquired >= self.limit:
            fut = Future(loop=self.service_client.loop)
            self._waiters.append(fut)
            yield from fut
        else:
            self._acquire()

    @coroutine
    def on_response(self, endpoint_desc, session, request_params, response):
        self._release()

    @coroutine
    def on_exception(self, endpoint_desc, session, request_params, ex):
        self._release()
