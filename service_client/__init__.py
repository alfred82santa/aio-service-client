import logging
from asyncio import coroutine, get_event_loop
from urllib.parse import urlparse, urlunsplit
from aiohttp.client import ClientSession
from aiohttp.connector import TCPConnector


class SessionWrapper:

    def __init__(self, session):
        self.set_custom_session(session)

    def __getattr__(self, item):  # pragma: no cover
        return getattr(self._session, item)

    def __setattr__(self, key, value):  # pragma: no cover
        return setattr(self._session, key, value)

    def __str__(self):  # pragma: no cover
        return str(self._session)

    def __repr__(self):  # pragma: no cover
        return repr(self._session)

    def __eq__(self, other):
        return self._session.__eq__(other)

    def set_attr_wrap(self, key, value):
        super(SessionWrapper, self).__setattr__(key, value)

    def set_custom_session(self, session):
        super(SessionWrapper, self).__setattr__('_session', session)


class ServiceClient:

    def __init__(self, rest_service_name='GenericService', spec=None, plugins=None, config=None,
                 parser=None, serializer=None, base_path='', loop=None, logger=None):
        self._plugins = []

        self.logger = logger or logging.getLogger('serviceClient.{}'.format(rest_service_name))
        self.rest_service_name = rest_service_name
        self.spec = spec or {}
        self.add_plugins(plugins or [])
        self.config = config or {}
        self.parser = parser or (lambda x, *args, **kwargs: x)
        self.serializer = serializer or (lambda x, *args, **kwargs: x)
        self.base_path = base_path
        self.loop = loop or get_event_loop()

        self.connector = TCPConnector(loop=self.loop, **self.config.get('connector', {}))
        self.session = ClientSession(connector=self.connector, loop=self.loop)

    @coroutine
    def call(self, service_name, payload=None, **kwargs):
        self.logger.debug("Calling service_client {0}...".format(service_name))
        service_desc = self.spec[service_name].copy()
        service_desc['service_name'] = service_name

        request_params = kwargs
        session = yield from self.prepare_session(service_desc, request_params)

        request_params['url'] = yield from self.generate_path(service_desc, session, request_params)
        request_params['method'] = service_desc.get('method', 'GET').upper()

        yield from self.prepare_request_params(service_desc, session, request_params)

        self.logger.info("Calling service_client {0} using {1} {2}".format(service_name,
                                                                           request_params['method'],
                                                                           request_params['url']))

        payload = yield from self.prepare_payload(service_desc, session, request_params, payload)
        try:
            if request_params['method'] not in ['GET', 'DELETE']:
                try:
                    stream_request = service_desc['stream_request']
                except KeyError:
                    stream_request = False
                if payload and not stream_request:
                    request_params['data'] = self.serializer(payload, session=session,
                                                             service_desc=service_desc,
                                                             request_params=request_params)

            yield from self.before_request(service_desc, session, request_params)

            response = yield from session.request(**request_params)
        except Exception as e:
            self.logger.warn("Exception calling service_client {0}: {1}".format(service_name, e))
            yield from self.on_exception(service_desc, session, request_params, e)
            raise e

        yield from self.on_response(service_desc, session, request_params, response)

        try:
            if service_desc['stream_response']:
                return response
        except KeyError:
            pass

        try:
            self.logger.info("Parsing response from {0}...".format(service_name))
            response.data = self.parser((yield from response.read()),
                                        session=session,
                                        service_desc=service_desc,
                                        response=response)
            yield from self.on_parsed_response(service_desc, session, request_params, response)
        except Exception as e:
            self.logger.warn("[Response code: {0}] Exception parsing response from service_client "
                             "{1}: {2}".format(response.status, service_name, e))
            yield from self.on_parse_exception(service_desc, session, request_params, response, e)
            e.response = response
            raise e

        return response

    @coroutine
    def prepare_session(self, service_desc, request_params):
        session = SessionWrapper(self.session)
        yield from self._execute_plugin_hooks('prepare_session', service_desc=service_desc, session=session,
                                              request_params=request_params)
        return session

    @coroutine
    def generate_path(self, service_desc, session, request_params):
        path = service_desc.get('path', '')
        url = list(urlparse(self.base_path))
        url[2] = '/'.join([url[2].rstrip('/'), path.lstrip('/')])
        url.pop()
        path = urlunsplit(url)
        hooks = [getattr(plugin, 'prepare_path') for plugin in self._plugins
                 if hasattr(plugin, 'prepare_path')]
        self.logger.debug("Calling {0} plugin hooks...".format('prepare_path'))
        for func in hooks:
            path = yield from func(service_desc=service_desc, session=session,
                                   request_params=request_params, path=path)

        return path

    @coroutine
    def prepare_request_params(self, service_desc, session, request_params):
        yield from self._execute_plugin_hooks('prepare_request_params', service_desc=service_desc,
                                              session=session, request_params=request_params)

    @coroutine
    def prepare_payload(self, service_desc, session, request_params, payload):
        hooks = [getattr(plugin, 'prepare_payload') for plugin in self._plugins
                 if hasattr(plugin, 'prepare_payload')]
        self.logger.debug("Calling {0} plugin hooks...".format('prepare_payload'))
        for func in hooks:
            payload = yield from func(service_desc=service_desc, session=session,
                                      request_params=request_params, payload=payload)
        return payload

    @coroutine
    def before_request(self, service_desc, session, request_params):
        yield from self._execute_plugin_hooks('before_request', service_desc=service_desc,
                                              session=session, request_params=request_params)

    @coroutine
    def on_exception(self, service_desc, session, request_params, ex):
        yield from self._execute_plugin_hooks('on_exception', service_desc=service_desc,
                                              session=session, request_params=request_params, ex=ex)

    @coroutine
    def on_response(self, service_desc, session, request_params, response):
        yield from self._execute_plugin_hooks('on_response', service_desc=service_desc,
                                              session=session, request_params=request_params, response=response)

    @coroutine
    def on_parse_exception(self, service_desc, session, request_params, response, ex):
        yield from self._execute_plugin_hooks('on_parse_exception', service_desc=service_desc,
                                              session=session, request_params=request_params, response=response, ex=ex)

    @coroutine
    def on_parsed_response(self, service_desc, session, request_params, response):
        yield from self._execute_plugin_hooks('on_parsed_response', service_desc=service_desc, session=session,
                                              request_params=request_params, response=response)

    @coroutine
    def _execute_plugin_hooks(self, hook, *args, **kwargs):
        hooks = [getattr(plugin, hook) for plugin in self._plugins if hasattr(plugin, hook)]
        self.logger.debug("Calling {0} plugin hooks...".format(hook))
        for func in hooks:
            yield from func(*args, **kwargs)

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
