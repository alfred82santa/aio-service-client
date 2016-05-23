'''
Created on 04/04/2014

@author: alfred
'''
import logging
from asyncio import coroutine, TimeoutError
from asyncio.tasks import sleep
from datetime import datetime, timedelta
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse
from aiohttp.multidict import CIMultiDict
from asynctest.case import TestCase
from service_client import SessionWrapper
from service_client.plugins import PathTokens, Timeout, Headers, QueryParams, Elapsed, InnerLogger, OuterLogger


class PathTest(TestCase):

    def setUp(self):
        self.plugin = PathTokens()
        self.session = ClientSession()
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def testNoChanges(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.endpoint_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/path/noway')),
                         '/test/path/noway')

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar'})

    @coroutine
    def testOneParam(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.endpoint_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/{path_param1}/noway')),
                         '/test/foo/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})

    @coroutine
    def testOneSpecialParam(self):
        request_params = {'path_param1': '*'}
        self.assertEqual((yield from self.plugin.prepare_path(self.endpoint_desc,
                                                              self.session,
                                                              request_params,
                                                              '/test/{path_param1}/noway')),
                         '/test/%2A/noway')

        self.assertDictEqual(request_params, {})

    @coroutine
    def testOneIntParam(self):
        request_params = {'path_param1': 1}
        self.assertEqual((yield from self.plugin.prepare_path(self.endpoint_desc,
                                                              self.session,
                                                              request_params,
                                                              '/test/{path_param1}/noway')),
                         '/test/1/noway')

        self.assertDictEqual(request_params, {})

    @coroutine
    def testTwoParams(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.endpoint_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/{path_param1}/{path_param2}/noway')),
                         '/test/foo/bar/noway')

        self.assertDictEqual(self.request_params, {})

    @coroutine
    def testTwoParamsRepeated(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.endpoint_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/{path_param1}/{path_param1}/noway')),
                         '/test/foo/foo/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})

    @coroutine
    def testNoParam(self):
        self.assertEqual((yield from self.plugin.prepare_path(self.endpoint_desc,
                                                              self.session,
                                                              self.request_params,
                                                              '/test/{path_param1}/{path_param3}/noway')),
                         '/test/foo/{path_param3}/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})


class TimeoutTest(TestCase):

    def setUp(self):

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                yield from sleep(0.5)
                raise Exception("No timeout")

        self.plugin = Timeout(default_timeout=0.1)
        self.session = SessionWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_use_default(self):
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        t = datetime.now()
        with self.assertRaises(TimeoutError):
            yield from self.session.request()
        self.assertGreater(datetime.now() - t, timedelta(seconds=0.1))
        self.assertLess(datetime.now() - t, timedelta(seconds=0.2))

    @coroutine
    def test_use_service(self):
        self.endpoint_desc['timeout'] = 0.2
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        t = datetime.now()
        with self.assertRaises(TimeoutError):
            yield from self.session.request()
        self.assertGreater(datetime.now() - t, timedelta(seconds=0.2))
        self.assertLess(datetime.now() - t, timedelta(seconds=0.3))

    @coroutine
    def test_use_request(self):
        self.endpoint_desc['timeout'] = 0.2
        self.request_params['timeout'] = 0.3
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        t = datetime.now()
        with self.assertRaises(TimeoutError):
            yield from self.session.request()
        self.assertGreater(datetime.now() - t, timedelta(seconds=0.3))
        self.assertLess(datetime.now() - t, timedelta(seconds=0.4))

    @coroutine
    def test_no_timeout(self):
        self.request_params['timeout'] = None
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        with self.assertRaisesRegex(Exception, "No timeout"):
            yield from self.session.request()


class HeadersTest(TestCase):

    def setUp(self):
        self.plugin = Headers(default_headers={'x-foo-bar': 'test headers'})
        self.session = ClientSession()
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_use_default(self):
        yield from self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers'}})

    @coroutine
    def test_use_service(self):
        self.endpoint_desc['headers'] = {'x-foo-bar': 'test headers service_client'}
        yield from self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers service_client'}})

    @coroutine
    def test_add_from_service(self):
        self.endpoint_desc['headers'] = {'x-foo-bar-service': 'test headers service_client'}
        yield from self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers',
                                                               'X-FOO-BAR-SERVICE': 'test headers service_client'}})

    @coroutine
    def test_use_request(self):
        self.endpoint_desc['headers'] = {'x-foo-bar': 'test headers service_client'}
        self.request_params['headers'] = {'x-foo-bar': 'test headers request'}
        yield from self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers request'}})

    @coroutine
    def test_add_from_request(self):
        self.endpoint_desc['headers'] = {'x-foo-bar-service': 'test headers service_client'}
        self.request_params['headers'] = {'x-foo-bar-request': 'test headers request'}
        yield from self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'headers': {'X-FOO-BAR': 'test headers',
                                                               'X-FOO-BAR-SERVICE': 'test headers service_client',
                                                               'X-FOO-BAR-REQUEST': 'test headers request'}})


class QueryParamsTest(TestCase):

    def setUp(self):
        self.plugin = QueryParams()
        self.session = ClientSession()
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada',
                              'query_params': {'qparam1': 1, 'qparam2': 'test2'}}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_use_default(self):
        yield from self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {'qparam1': 1, 'qparam2': 'test2'}})

    @coroutine
    def test_use_request(self):
        self.request_params['params'] = {'qparamRequest': 'test'}
        yield from self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {
                                                       'qparam1': 1,
                                                       'qparam2': 'test2',
                                                       'qparamRequest': 'test'}})


class ElapsedTest(TestCase):

    spend_time = 0.1

    def setUp(self):

        this = self

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                yield from sleep(this.spend_time)
                response = ClientResponse('get', 'http://test.test')
                response._post_init(this.loop)
                return response

        self.plugin = Elapsed()
        self.session = SessionWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_elapsed(self):
        yield from self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)

        response = yield from self.session.request()
        self.assertGreater(response.elapsed, timedelta(seconds=0.1))
        self.assertLess(response.elapsed, timedelta(seconds=0.2))

    @coroutine
    def test_elapsed_2(self):
        self.spend_time = 0.2
        yield from self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)

        response = yield from self.session.request()
        self.assertGreater(response.elapsed, timedelta(seconds=0.2))
        self.assertLess(response.elapsed, timedelta(seconds=0.3))


class InnerLogTest(TestCase):

    def setUp(self):

        this = self

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                response = ClientResponse('get', 'http://test.test')
                response._post_init(this.loop)
                response._content = b'ssssssss'
                response.status = 200
                response.elapsed = timedelta(seconds=100)
                response.headers = CIMultiDict({"content-type": "application/json"})
                return response

        class LoggerMock:

            def log(self, level, message, *args, **kwargs):
                self.level = level
                self.message = message
                self.args = args
                self.kwargs = kwargs

        class ServiceMock:

            name = 'test_service'

        self.logger = LoggerMock()
        self.plugin = InnerLogger(self.logger, max_body_length=3)

        self.service = ServiceMock()
        self.plugin.assign_service_client(self.service)

        self.session = SessionWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'POST',
                              'param1': 'obladi',
                              'param2': 'oblada',
                              'endpoint': 'test_endpoint'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_before_request(self):

        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Sending request")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'REQUEST',
                                    'body': '<NO BODY>',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'tracking_token': self.session.tracking_token}})

    @coroutine
    def test_before_request_with_data(self):
        self.request_params['data'] = 'data text'
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Sending request")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'REQUEST',
                                    'body': 'dat',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'tracking_token': self.session.tracking_token}})

    @coroutine
    def test_on_exception(self):
        ex = AttributeError('Testing Exception')
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)
        yield from self.plugin.on_exception(self.endpoint_desc, self.session, self.request_params, ex)

        self.assertEqual(self.logger.level, logging.CRITICAL)
        self.assertEqual(self.logger.message, "Testing Exception")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'EXCEPTION',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'exception': ex,
                                    'tracking_token': self.session.tracking_token}})

    @coroutine
    def test_on_response(self):
        resp = yield from self.session.request()
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)
        yield from self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, resp)

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Response received")
        self.assertEqual(self.logger.args, tuple())
        self.maxDiff = None
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'RESPONSE',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'status_code': resp.status,
                                    'body': 'sss',
                                    'elapsed': resp.elapsed,
                                    'headers': resp.headers,
                                    'tracking_token': self.session.tracking_token}})

    @coroutine
    def test_on_parse_exception(self):
        ex = AttributeError('Testing Exception')
        resp = yield from self.session.request()
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)
        yield from self.plugin.on_parse_exception(self.endpoint_desc, self.session, self.request_params, resp, ex)

        self.assertEqual(self.logger.level, logging.CRITICAL)
        self.assertEqual(self.logger.message, "Testing Exception")
        self.assertEqual(self.logger.args, tuple())
        self.maxDiff = None
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'EXCEPTION',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'status_code': resp.status,
                                    'body': 'sss',
                                    'elapsed': resp.elapsed,
                                    'headers': resp.headers,
                                    'exception': ex,
                                    'tracking_token': self.session.tracking_token}})


class OuterLogTest(TestCase):

    def setUp(self):
        this = self

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                response = ClientResponse('get', 'http://test.test')
                response._post_init(this.loop)
                response._content = b'ssssssss'
                response.status = 200
                response.elapsed = timedelta(seconds=100)
                response.headers = CIMultiDict({"content-type": "application/json"})
                return response

        class LoggerMock:

            def log(self, level, message, *args, **kwargs):
                self.level = level
                self.message = message
                self.args = args
                self.kwargs = kwargs

        class ServiceMock:
            name = 'test_service'

        self.logger = LoggerMock()
        self.plugin = OuterLogger(self.logger, max_body_length=3)

        self.service = ServiceMock()
        self.plugin.assign_service_client(self.service)

        self.session = SessionWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'POST',
                              'param1': 'obladi',
                              'param2': 'oblada',
                              'endpoint': 'test_endpoint'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_prepare_payload(self):
        yield from self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, 'aaaaa')

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Sending request")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'REQUEST',
                                    'body': 'aaa',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'tracking_token': self.session.tracking_token}})

    @coroutine
    def test_prepare_payload_with_no_data(self):
        yield from self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, None)

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Sending request")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'REQUEST',
                                    'body': '<NO BODY>',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'tracking_token': self.session.tracking_token}})

    @coroutine
    def test_on_exception(self):
        ex = AttributeError('Testing Exception')
        yield from self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, None)
        yield from self.plugin.on_exception(self.endpoint_desc, self.session, self.request_params, ex)

        self.assertEqual(self.logger.level, logging.CRITICAL)
        self.assertEqual(self.logger.message, "Testing Exception")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'EXCEPTION',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'exception': ex,
                                    'tracking_token': self.session.tracking_token}})

    @coroutine
    def test_on_parse_response(self):
        resp = yield from self.session.request()
        resp.data = 'bbbbb'
        yield from self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, None)
        yield from self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, resp)

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Response received")
        self.assertEqual(self.logger.args, tuple())
        self.maxDiff = None
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'RESPONSE',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'status_code': resp.status,
                                    'body': 'bbb',
                                    'elapsed': resp.elapsed,
                                    'headers': resp.headers,
                                    'tracking_token': self.session.tracking_token}})

    @coroutine
    def test_on_parse_exception(self):
        ex = AttributeError('Testing Exception')
        resp = yield from self.session.request()
        yield from self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, None)
        yield from self.plugin.on_parse_exception(self.endpoint_desc, self.session, self.request_params, resp, ex)

        self.assertEqual(self.logger.level, logging.CRITICAL)
        self.assertEqual(self.logger.message, "Testing Exception")
        self.assertEqual(self.logger.args, tuple())
        self.maxDiff = None
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'EXCEPTION',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service',
                                    'status_code': resp.status,
                                    'body': 'sss',
                                    'elapsed': resp.elapsed,
                                    'headers': resp.headers,
                                    'exception': ex,
                                    'tracking_token': self.session.tracking_token}})
