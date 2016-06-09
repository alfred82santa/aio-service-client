import logging
from asyncio import coroutine, get_event_loop
from asyncio.tasks import Task
from urllib.parse import urlparse, urlunsplit
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse
from aiohttp.connector import TCPConnector
from .utils import ObjectWrapper


class ServiceClient:

    def __init__(self, name='GenericService', spec=None, plugins=None, config=None,
                 parser=None, serializer=None, base_path='', loop=None, logger=None):
        self._plugins = []

        self.logger = logger or logging.getLogger('serviceClient.{}'.format(name))
        self.name = name
        self.spec = spec or {}
        self.add_plugins(plugins or [])
        self.config = config or {}
        self.parser = parser or (lambda x, *args, **kwargs: x)
        self.serializer = serializer or (lambda x, *args, **kwargs: x)
        self.base_path = base_path
        self.loop = loop or get_event_loop()

        self.connector = TCPConnector(loop=self.loop, **self.config.get('connector', {}))
        self.session = ClientSession(connector=self.connector, loop=self.loop,
                                     response_class=self.create_response,
                                     **self.config.get('session', {}))

    def create_response(self, *args, **kwargs):
        response = ObjectWrapper(ClientResponse(*args, **kwargs))
        task = Task.current_task(loop=self.loop)

        self._execute_plugin_hooks_sync('prepare_response',
                                        endpoint_desc=task.endpoint_desc, session=task.session,
                                        request_params=task.request_params,
                                        response=response)

        return response

    @coroutine
    def call(self, endpoint, payload=None, **kwargs):
        self.logger.debug("Calling service {0}...".format(endpoint))
        endpoint_desc = self.spec[endpoint].copy()
        endpoint_desc['endpoint'] = endpoint

        request_params = kwargs
        session = yield from self.prepare_session(endpoint_desc, request_params)

        request_params['url'] = yield from self.generate_path(endpoint_desc, session, request_params)
        request_params['method'] = endpoint_desc.get('method', 'GET').upper()

        yield from self.prepare_request_params(endpoint_desc, session, request_params)

        self.logger.info("Calling service {0} using {1} {2}".format(endpoint,
                                                                    request_params['method'],
                                                                    request_params['url']))

        payload = yield from self.prepare_payload(endpoint_desc, session, request_params, payload)
        try:
            if request_params['method'] not in ['GET', 'DELETE']:
                try:
                    stream_request = endpoint_desc['stream_request']
                except KeyError:
                    stream_request = False
                if payload:
                    if stream_request:
                        request_params['data'] = payload
                    else:
                        request_params['data'] = self.serializer(payload, session=session,
                                                                 endpoint_desc=endpoint_desc,
                                                                 request_params=request_params)

            yield from self.before_request(endpoint_desc, session, request_params)
            task = Task.current_task(loop=self.loop)
            task.session = session
            task.endpoint_desc = endpoint_desc
            task.request_params = request_params
            response = yield from session.request(**request_params)
        except Exception as e:
            self.logger.warn("Exception calling service {0}: {1}".format(endpoint, e))
            yield from self.on_exception(endpoint_desc, session, request_params, e)
            raise e

        yield from self.on_response(endpoint_desc, session, request_params, response)

        try:
            if endpoint_desc['stream_response']:
                return response
        except KeyError:
            pass

        try:
            data = yield from response.read()
            yield from self.on_read(endpoint_desc, session, request_params, response)
            self.logger.info("Parsing response from {0}...".format(endpoint))
            response.data = self.parser(data,
                                        session=session,
                                        endpoint_desc=endpoint_desc,
                                        response=response)
            yield from self.on_parsed_response(endpoint_desc, session, request_params, response)
        except Exception as e:
            self.logger.warn("[Response code: {0}] Exception parsing response from service "
                             "{1}: {2}".format(response.status, endpoint, e))
            yield from self.on_parse_exception(endpoint_desc, session, request_params, response, e)
            e.response = response
            raise e

        return response

    @coroutine
    def prepare_session(self, endpoint_desc, request_params):
        session = ObjectWrapper(self.session)
        yield from self._execute_plugin_hooks('prepare_session', endpoint_desc=endpoint_desc, session=session,
                                              request_params=request_params)
        return session

    @coroutine
    def generate_path(self, endpoint_desc, session, request_params):
        path = endpoint_desc.get('path', '')
        url = list(urlparse(self.base_path))
        url[2] = '/'.join([url[2].rstrip('/'), path.lstrip('/')])
        url.pop()
        path = urlunsplit(url)
        hooks = [getattr(plugin, 'prepare_path') for plugin in self._plugins
                 if hasattr(plugin, 'prepare_path')]
        self.logger.debug("Calling {0} plugin hooks...".format('prepare_path'))
        for func in hooks:
            path = yield from func(endpoint_desc=endpoint_desc, session=session,
                                   request_params=request_params, path=path)

        return path

    @coroutine
    def prepare_request_params(self, endpoint_desc, session, request_params):
        yield from self._execute_plugin_hooks('prepare_request_params', endpoint_desc=endpoint_desc,
                                              session=session, request_params=request_params)

    @coroutine
    def prepare_payload(self, endpoint_desc, session, request_params, payload):
        hooks = [getattr(plugin, 'prepare_payload') for plugin in self._plugins
                 if hasattr(plugin, 'prepare_payload')]
        self.logger.debug("Calling {0} plugin hooks...".format('prepare_payload'))
        for func in hooks:
            payload = yield from func(endpoint_desc=endpoint_desc, session=session,
                                      request_params=request_params, payload=payload)
        return payload

    @coroutine
    def before_request(self, endpoint_desc, session, request_params):
        yield from self._execute_plugin_hooks('before_request', endpoint_desc=endpoint_desc,
                                              session=session, request_params=request_params)

    @coroutine
    def on_exception(self, endpoint_desc, session, request_params, ex):
        yield from self._execute_plugin_hooks('on_exception', endpoint_desc=endpoint_desc,
                                              session=session, request_params=request_params, ex=ex)

    @coroutine
    def on_response(self, endpoint_desc, session, request_params, response):
        yield from self._execute_plugin_hooks('on_response', endpoint_desc=endpoint_desc,
                                              session=session, request_params=request_params, response=response)

    @coroutine
    def on_read(self, endpoint_desc, session, request_params, response):
        yield from self._execute_plugin_hooks('on_read', endpoint_desc=endpoint_desc,
                                              session=session, request_params=request_params, response=response)

    @coroutine
    def on_parse_exception(self, endpoint_desc, session, request_params, response, ex):
        yield from self._execute_plugin_hooks('on_parse_exception', endpoint_desc=endpoint_desc,
                                              session=session, request_params=request_params, response=response, ex=ex)

    @coroutine
    def on_parsed_response(self, endpoint_desc, session, request_params, response):
        yield from self._execute_plugin_hooks('on_parsed_response', endpoint_desc=endpoint_desc, session=session,
                                              request_params=request_params, response=response)

    @coroutine
    def _execute_plugin_hooks(self, hook, *args, **kwargs):
        hooks = [getattr(plugin, hook) for plugin in self._plugins if hasattr(plugin, hook)]
        self.logger.debug("Calling {0} plugin hooks...".format(hook))
        for func in hooks:
            yield from func(*args, **kwargs)

    def _execute_plugin_hooks_sync(self, hook, *args, **kwargs):
        hooks = [getattr(plugin, hook) for plugin in self._plugins if hasattr(plugin, hook)]
        self.logger.debug("Calling {0} plugin hooks...".format(hook))
        for func in hooks:
            func(*args, **kwargs)

    def add_plugins(self, plugins):
        self._plugins.extend(plugins)

        hook = 'assign_service_client'
        hooks = [getattr(plugin, hook) for plugin in self._plugins if hasattr(plugin, hook)]
        self.logger.debug("Calling {0} plugin hooks...".format(hook))
        for func in hooks:
            func(service_client=self)

    def __getattr__(self, item):

        @coroutine
        def wrap(*args, **kwargs):

            return self.call(item, *args, **kwargs)

        return wrap

    def __del__(self):  # pragma: no cover
        self.session.close()
