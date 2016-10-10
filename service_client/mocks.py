from aiohttp.client_reqrep import ClientResponse
from multidict import CIMultiDict
from functools import wraps
from asyncio import coroutine, get_event_loop
from dirty_loader import LoaderNamespaceReversedCached
from .plugins import BasePlugin


class NoMock(Exception):
    pass


class BaseMockDefinition:

    def __init__(self, mock_manager, service_name=None, endpoint=None, offset=0, limit=1):
        self.mock_manager = mock_manager
        self.service_name = service_name
        self.endpoint = endpoint
        self.offset = offset if offset >= 0 else 0
        self.limit = limit if limit >= 0 else 1

    def __call__(self, func):
        @wraps(func)
        @coroutine
        def inner(*args, **kwargs):
            with self:
                yield from func(*args, **kwargs)

        return inner

    def __enter__(self):
        self.mock_manager.push(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mock_manager.pop(self)


class PatchMockDescDefinition(BaseMockDefinition):

    def __init__(self, patch, *args, **kwargs):
        super(PatchMockDescDefinition, self).__init__(*args, **kwargs)
        self.patch = patch


class UseMockDefinition(BaseMockDefinition):

    def __init__(self, mock, *args, **kwargs):
        super(UseMockDefinition, self).__init__(*args, **kwargs)
        self.mock = mock


class MockManager:

    def __init__(self):
        self.mocks = []

    def patch_mock_desc(self, patch, *args, **kwarg):
        """
        Context manager or decorator in order to patch a mock definition of service
        endpoint in a test.

        :param patch: Dictionary in order to update endpoint's mock definition
        :type patch: dict
        :param service_name: Name of service where you want to use mock. If None it will be used
            as soon as possible.
        :type service_name: str
        :param endpoint: Endpoint where you want to use mock. If None it will be used
            as soon as possible.
        :type endpoint: str
        :param offset: Times it must be ignored before use. Default 0. Only positive integers.
        :type offset: int
        :param limit: Times it could be used. Default 1. 0 means no limit. Only positive integers.
        :type limit: int
        :return: PatchMockDescDefinition
        """

        return PatchMockDescDefinition(patch, self, *args, **kwarg)

    def use_mock(self, mock, *args, **kwarg):
        """
        Context manager or decorator in order to use a coroutine as mock of service
        endpoint in a test.

        :param mock: Coroutine to use as mock. It should behave like :meth:`~ClientSession.request`.
        :type mock: coroutine
        :param service_name: Name of service where you want to use mock. If None it will be used
            as soon as possible.
        :type service_name: str
        :param endpoint: Endpoint where you want to use mock. If None it will be used
            as soon as possible.
        :type endpoint: str
        :param offset: Times it must be ignored before use. Default 0. Only positive integers.
        :type offset: int
        :param limit: Times it could be used. Default 1. 0 means no limit. Only positive integers.
        :type limit: int
        :return: UseMockDefinition
        """
        return UseMockDefinition(mock, self, *args, **kwarg)

    def push(self, mock_description):
        self.mocks.insert(0, mock_description)

    def pop(self, mock_description):
        try:
            self.mocks.remove(mock_description)
        except ValueError:  # pragma: no cover
            pass

    def next_mock(self, service_name, endpoint):
        for i in range(len(self.mocks)):
            candidate = self.mocks[i]
            if (candidate.service_name is not None and candidate.service_name != service_name) \
                    or (candidate.endpoint is not None and candidate.endpoint != endpoint):
                continue

            if candidate.offset > 0:
                candidate.offset -= 1
                continue

            if candidate.limit > 1:
                candidate.limit -= 1
            else:
                self.mocks.pop(i)

            return candidate

        raise NoMock()


mock_manager = MockManager()


class Mock(BasePlugin):

    def __init__(self, namespaces=None):

        self.loader = LoaderNamespaceReversedCached()
        self.loader.register_namespace('default', __name__)

        if namespaces:
            for n, m in namespaces.items():
                self.loader.register_namespace(n, m)

    def _create_mock(self, endpoint_desc, session, request_params, mock_desc, loop):
        """
        The class imported should have the __call__ function defined to be an object directly callable
        """
        try:
            mock_def = mock_manager.next_mock(self.service_client.name,
                                              endpoint_desc['endpoint'])

            if isinstance(mock_def, PatchMockDescDefinition):
                mock_desc.update(mock_def.patch)
            else:
                return mock_def.mock
        except NoMock:
            pass

        return self.loader.factory(mock_desc.get('mock_type'),
                                   endpoint_desc, session,
                                   request_params, mock_desc,
                                   loop=loop)

    @coroutine
    def prepare_session(self, endpoint_desc, session, request_params):
        mock_desc = endpoint_desc.get('mock', {})
        session.override_attr('request', self._create_mock(endpoint_desc,
                                                           session,
                                                           request_params,
                                                           mock_desc.copy(),
                                                           loop=self.service_client.loop))

        try:
            session.request.set_request_params(request_params)
        except AttributeError:
            pass


class BaseMock:

    def __init__(self, endpoint_desc, session, request_params,
                 mock_desc, loop=None):
        self.endpoint_desc = endpoint_desc
        self.session = session
        self.request_params = request_params
        self.mock_desc = mock_desc
        self.loop = loop or get_event_loop()

    @coroutine
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

        self.method = method
        self.url = url
        self.args = args
        self.kwargs = kwargs
        self.response = ClientResponse(method, url)
        self.response._post_init(self.loop)
        self.response.status = self.mock_desc.get('status', 200)
        self.response.headers = CIMultiDict(self.mock_desc.get('headers', {}))

        yield from self.prepare_response()

        return self.response


class BaseFileMock(BaseMock):

    @coroutine
    def prepare_response(self):
        filename = self.mock_desc['file']
        self.response._content = self.load_file(filename)


class RawFileMock(BaseFileMock):

    def load_file(self, filename):
        return open(filename, "rb").read()
