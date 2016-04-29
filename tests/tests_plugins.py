'''
Created on 04/04/2014

@author: alfred
'''
from asyncio import coroutine
from aiohttp.client import ClientSession
from asynctest.case import TestCase

from service_client import SessionWrapper
from service_client.plugins import Path, Timeout, Headers, QueryParams, Mock


class PathTest(TestCase):

    def setUp(self):
        self.plugin = Path()
        self.session = ClientSession()
        self.service_desc = {'path': '/test1/path/noway',
                             'method': 'GET',
                             'param1': 'obladi',
                             'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def testNoChanges(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.service_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/path/noway')),
                         '/test/path/noway')

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar'})

    @coroutine
    def testOneParam(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.service_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/{path_param1}/noway')),
                         '/test/foo/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})

    @coroutine
    def testOneSpecialParam(self):
        request_params = {'path_param1': '*'}
        self.assertEqual((yield from self.plugin.prepare_path(self.service_desc,
                                                              self.session,
                                                              request_params,
                                                              '/test/{path_param1}/noway')),
                         '/test/%2A/noway')

        self.assertDictEqual(request_params, {})

    @coroutine
    def testOneIntParam(self):
        request_params = {'path_param1': 1}
        self.assertEqual((yield from self.plugin.prepare_path(self.service_desc,
                                                              self.session,
                                                              request_params,
                                                              '/test/{path_param1}/noway')),
                         '/test/1/noway')

        self.assertDictEqual(request_params, {})

    @coroutine
    def testTwoParams(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.service_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/{path_param1}/{path_param2}/noway')),
                         '/test/foo/bar/noway')

        self.assertDictEqual(self.request_params, {})

    @coroutine
    def testTwoParamsRepeated(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.service_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/{path_param1}/{path_param1}/noway')),
                         '/test/foo/foo/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})

    @coroutine
    def testNoParam(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.service_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/{path_param1}/{path_param3}/noway')),
                         '/test/foo/{path_param3}/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})


class TimeoutTest(TestCase):

    def setUp(self):
        self.plugin = Timeout(default_timeout=34)
        self.session = ClientSession()
        self.service_desc = {'path': '/test1/path/noway',
                             'method': 'GET',
                             'param1': 'obladi',
                             'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_use_default(self):
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'timeout': 34})

    @coroutine
    def test_use_service(self):
        self.service_desc['timeout'] = 12
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'timeout': 12})

    @coroutine
    def test_use_request(self):
        self.service_desc['timeout'] = 12
        self.request_params['timeout'] = 65
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'timeout': 65})


class HeadersTest(TestCase):

    def setUp(self):
        self.plugin = Headers(default_headers={'x-foo-bar': 'test headers'})
        self.session = ClientSession()
        self.service_desc = {'path': '/test1/path/noway',
                             'method': 'GET',
                             'param1': 'obladi',
                             'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_use_default(self):
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers'}})

    @coroutine
    def test_use_service(self):
        self.service_desc['headers'] = {'x-foo-bar': 'test headers service_client'}
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers service_client'}})

    @coroutine
    def test_add_from_service(self):
        self.service_desc['headers'] = {'x-foo-bar-service': 'test headers service_client'}
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers',
                                                               'X-FOO-BAR-SERVICE': 'test headers service_client'}})

    @coroutine
    def test_use_request(self):
        self.service_desc['headers'] = {'x-foo-bar': 'test headers service_client'}
        self.request_params['headers'] = {'x-foo-bar': 'test headers request'}
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers request'}})

    @coroutine
    def test_add_from_request(self):
        self.service_desc['headers'] = {'x-foo-bar-service': 'test headers service_client'}
        self.request_params['headers'] = {'x-foo-bar-request': 'test headers request'}
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers',
                                                               'X-FOO-BAR-SERVICE': 'test headers service_client',
                                                               'X-FOO-BAR-REQUEST': 'test headers request'}})


class QueryParamsTest(TestCase):

    def setUp(self):
        self.plugin = QueryParams()
        self.session = ClientSession()
        self.service_desc = {'path': '/test1/path/noway',
                             'method': 'GET',
                             'param1': 'obladi',
                             'param2': 'oblada',
                             'query_params': {'qparam1': 1, 'qparam2': 'test2'}}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_use_default(self):
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {'qparam1': 1, 'qparam2': 'test2'}})

    @coroutine
    def test_use_request(self):
        self.request_params['params'] = {'qparamRequest': 'test'}
        yield from self.plugin.prepare_request_params(self.service_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {
                                                       'qparam1': 1,
                                                       'qparam2': 'test2',
                                                       'qparamRequest': 'test'}})


class TestMocker(TestCase):

    def setUp(self):
        self.plugin = Mock(namespaces={'mocks': 'tests.mocks'})
        self.session = SessionWrapper(ClientSession())
        self.service_desc = {'mock': {
            'mock_type': 'mocks:FakeMock',
            'file': 'data/mocks/opengate_v6/alarm/alarm_list.json'
        }}

        self.service_client = type('DynTestServiceClient', (),
                                   {'rest_service_name': 'test_service_name',
                                    'loop': self.loop})()
        self.plugin.assign_service_client(self.service_client)

    @coroutine
    def test_calling_mock(self):
        from .mocks import FakeMock
        yield from self.plugin.prepare_session(self.service_desc, self.session, {})
        self.assertIsInstance(self.session.request, FakeMock)
        response = self.session.request('POST', 'default_url')
        self.assertEqual(200, response.status)
