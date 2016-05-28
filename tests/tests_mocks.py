import os
from asyncio.coroutines import coroutine

from aiohttp import hdrs
from asynctest.case import TestCase
from aiohttp.client import ClientSession
from service_client.mocks import Mock, mock_manager, RawFileMock
from service_client.utils import ObjectWrapper

MOCKS_DIR = os.path.join(os.path.dirname(__file__), 'mock_files')


class RaiseExceptionMock:

    def __init__(self, exception):
        self.ex = exception

    @coroutine
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        raise self.ex


class TestMocker(TestCase):

    def setUp(self):
        self.plugin = Mock(namespaces={'mocks': 'tests.mocks'})
        self.session = ObjectWrapper(ClientSession())
        self.service_desc = {'mock': {'mock_type': 'mocks:FakeMock',
                                      'file': 'data/mocks/opengate_v6/alarm/alarm_list.json'},
                             'endpoint': 'test_endpoint'}

        self.service_client = type('DynTestServiceClient', (),
                                   {'name': 'test_service_name',
                                    'loop': self.loop})()
        self.plugin.assign_service_client(self.service_client)

    @coroutine
    def test_calling_mock(self):
        from .mocks import FakeMock
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, FakeMock)
        response = yield from self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)

    @mock_manager.use_mock(mock=RaiseExceptionMock(KeyError()))
    @coroutine
    def test_mocking_mock(self):
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, RaiseExceptionMock)
        with self.assertRaises(KeyError):
            yield from self.session.request('POST', 'default_url')

        from .mocks import FakeMock
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, FakeMock)
        response = yield from self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)

    @mock_manager.use_mock(mock=RaiseExceptionMock(KeyError()), limit=2)
    @coroutine
    def test_mocking_mock_with_limit(self):
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, RaiseExceptionMock)
        with self.assertRaises(KeyError):
            yield from self.session.request('POST', 'default_url')

        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, RaiseExceptionMock)
        with self.assertRaises(KeyError):
            yield from self.session.request('POST', 'default_url')

        from .mocks import FakeMock
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, FakeMock)
        response = yield from self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)

    @mock_manager.use_mock(mock=RaiseExceptionMock(KeyError()), limit=2, offset=1)
    @coroutine
    def test_mocking_mock_with_offset_and_limit(self):

        from .mocks import FakeMock
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, FakeMock)
        response = yield from self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)

        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, RaiseExceptionMock)
        with self.assertRaises(KeyError):
            yield from self.session.request('POST', 'default_url')

        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, RaiseExceptionMock)
        with self.assertRaises(KeyError):
            yield from self.session.request('POST', 'default_url')

        from .mocks import FakeMock
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, FakeMock)
        response = yield from self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)

    @mock_manager.use_mock(mock=RaiseExceptionMock(KeyError()), service_name='other_service')
    @coroutine
    def test_calling_mock_other_service(self):
        from .mocks import FakeMock
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, FakeMock)
        response = yield from self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)

    @mock_manager.use_mock(mock=RaiseExceptionMock(KeyError()), service_name='test_service_name',
                           endpoint='other_endpoint')
    @coroutine
    def test_calling_mock_other_endpoint(self):
        from .mocks import FakeMock
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, FakeMock)
        response = yield from self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)

    @mock_manager.use_mock(mock=RaiseExceptionMock(KeyError()), service_name='test_service_name',
                           endpoint='test_endpoint')
    @coroutine
    def test_calling_mock_same_endpoint(self):
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, RaiseExceptionMock)
        with self.assertRaises(KeyError):
            yield from self.session.request('POST', 'default_url')

    @mock_manager.patch_mock_desc(patch={'mock_type': 'default:RawFileMock',
                                         'file': os.path.join(MOCKS_DIR, 'test_mock_text.data'),
                                         'headers': {hdrs.CONTENT_TYPE: "text/plain; charset=utf8"}})
    @coroutine
    def test_patch_mock(self):
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, RawFileMock)
        response = yield from self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)
        self.assertEqual('test data', (yield from response.text()))
