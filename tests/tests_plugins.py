'''
Created on 04/04/2014

@author: alfred
'''
import asyncio
import logging
from asyncio import coroutine, TimeoutError
from asyncio.tasks import sleep, shield
from datetime import datetime, timedelta
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse
from aiohttp.multidict import CIMultiDict
from asynctest.case import TestCase
from service_client.utils import ObjectWrapper
from service_client.plugins import PathTokens, Timeout, Headers, QueryParams, Elapsed, InnerLogger, OuterLogger, \
    TrackingToken, Pool


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
        self.session = ObjectWrapper(SessionMock())
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


class TimeoutWithResponseTest(TestCase):

    def setUp(self):

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                yield from sleep(0.5)
                return 'response'

        self.plugin = Timeout(default_timeout=0.1)
        self.session = ObjectWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_no_timeout(self):
        self.request_params['timeout'] = None
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        self.assertEqual((yield from self.session.request()), 'response')


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


class ResponseMock:

    def __init__(self, spend_time):
        self.spend_time = spend_time

    @coroutine
    def start(self, *args, **kwargs):
        yield from sleep(self.spend_time)

    @coroutine
    def read(self):
        yield from sleep(self.spend_time)
        return 'data'


class ElapsedTest(TestCase):

    spend_time = 0.1

    def setUp(self):

        this = self

        class SessionMock:

            response = ObjectWrapper(ResponseMock(0.1))

            @coroutine
            def request(self, *args, **kwargs):
                yield from sleep(this.spend_time)
                self.response._post_init(this.loop)
                return self.response

        self.plugin = Elapsed()
        self.session = ObjectWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_headers_elapsed(self):
        response = ObjectWrapper(ResponseMock(0.1))
        self.plugin.prepare_response(self.endpoint_desc, self.session, self.request_params, response)

        t = datetime.now()
        yield from response.start()
        self.assertGreater(response.headers_elapsed, timedelta(seconds=0.1))
        self.assertLess(response.headers_elapsed, timedelta(seconds=0.2))
        self.assertGreater(response.start_headers, t)
        self.assertLess(response.start_headers, datetime.now())

    @coroutine
    def test_headers_elapsed_2(self):
        response = ObjectWrapper(ResponseMock(0.2))
        self.plugin.prepare_response(self.endpoint_desc, self.session, self.request_params, response)

        t = datetime.now()
        yield from response.start()
        self.assertGreater(response.headers_elapsed, timedelta(seconds=0.2))
        self.assertLess(response.headers_elapsed, timedelta(seconds=0.3))
        self.assertGreater(response.start_headers, t)
        self.assertLess(response.start_headers, datetime.now())

    @coroutine
    def test_no_headers_elapsed_endpoint(self):
        self.endpoint_desc['elapsed'] = {'headers': False}
        response = ObjectWrapper(ResponseMock(0.1))
        self.plugin.prepare_response(self.endpoint_desc, self.session, self.request_params, response)

        yield from response.start()
        self.assertFalse(hasattr(response, 'headers_elapsed'))
        self.assertFalse(hasattr(response, 'start_headers'))

    @coroutine
    def test_no_headers_elapsed_request_params(self):
        self.request_params['headers_elapsed'] = False
        response = ObjectWrapper(ResponseMock(0.1))
        self.plugin.prepare_response(self.endpoint_desc, self.session, self.request_params, response)

        yield from response.start()
        self.assertFalse(hasattr(response, 'headers_elapsed'))
        self.assertFalse(hasattr(response, 'start_headers'))

    @coroutine
    def test_read_elapsed(self):
        response = ObjectWrapper(ResponseMock(0.1))
        t = datetime.now()
        yield from self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)
        yield from sleep(0.1)
        yield from self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)

        self.assertGreater(response.read_elapsed, timedelta(seconds=0.1))
        self.assertLess(response.read_elapsed, timedelta(seconds=0.2))
        self.assertGreater(response.start_read, t)
        self.assertLess(response.start_read, datetime.now())

    @coroutine
    def test_read_elapsed_2(self):
        response = ObjectWrapper(ResponseMock(0.2))
        t = datetime.now()
        yield from self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)
        yield from sleep(0.2)
        yield from self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)

        self.assertGreater(response.read_elapsed, timedelta(seconds=0.2))
        self.assertLess(response.read_elapsed, timedelta(seconds=0.3))
        self.assertGreater(response.start_read, t)
        self.assertLess(response.start_read, datetime.now())

    @coroutine
    def test_no_read_elapsed_endpoint(self):
        self.endpoint_desc['elapsed'] = {'read': False}
        response = ObjectWrapper(ResponseMock(0.1))
        yield from self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)
        yield from self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)

        self.assertFalse(hasattr(response, 'read_elapsed'))
        self.assertFalse(hasattr(response, 'start_read'))

    @coroutine
    def test_no_read_elapsed_request_params(self):
        self.request_params['read_elapsed'] = False
        response = ObjectWrapper(ResponseMock(0.1))
        yield from self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)
        yield from self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)

        self.assertFalse(hasattr(response, 'read_elapsed'))
        self.assertFalse(hasattr(response, 'start_read'))

    @coroutine
    def test_parse_elapsed(self):
        response = ObjectWrapper(ResponseMock(0.1))
        t = datetime.now()
        yield from self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)
        yield from sleep(0.1)
        yield from self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertGreater(response.parse_elapsed, timedelta(seconds=0.1))
        self.assertLess(response.parse_elapsed, timedelta(seconds=0.2))
        self.assertGreater(response.start_parse, t)
        self.assertLess(response.start_parse, datetime.now())

    @coroutine
    def test_parse_elapsed_2(self):
        response = ObjectWrapper(ResponseMock(0.2))
        t = datetime.now()
        yield from self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)
        yield from sleep(0.2)
        yield from self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertGreater(response.parse_elapsed, timedelta(seconds=0.2))
        self.assertLess(response.parse_elapsed, timedelta(seconds=0.3))
        self.assertGreater(response.start_parse, t)
        self.assertLess(response.start_parse, datetime.now())

    @coroutine
    def test_no_parse_elapsed_endpoint(self):
        self.endpoint_desc['elapsed'] = {'parse': False}
        response = ObjectWrapper(ResponseMock(0.1))
        yield from self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)
        yield from self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertFalse(hasattr(response, 'parse_elapsed'))
        self.assertFalse(hasattr(response, 'start_parse'))

    @coroutine
    def test_no_parse_elapsed_request_params(self):
        self.request_params['parse_elapsed'] = False
        response = ObjectWrapper(ResponseMock(0.1))
        yield from self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)
        yield from self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertFalse(hasattr(response, 'parse_elapsed'))
        self.assertFalse(hasattr(response, 'start_parse'))


class TrackingTokenTest(TestCase):

    def setUp(self):

        this = self

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                response = ObjectWrapper(ClientResponse('get', 'http://test.test'))
                response._post_init(this.loop)
                return response

        self.plugin = TrackingToken(prefix='test-')
        self.session = ObjectWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_generate_tracking_token(self):
        yield from self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)

        self.assertTrue(self.session.tracking_token.startswith('test-'))
        self.assertEqual(len(self.session.tracking_token), 15)

    @coroutine
    def test_set_tracking_token(self):
        self.request_params['tracking_token'] = 'FOOBAR123'
        yield from self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)

        self.assertTrue(self.session.tracking_token.startswith('test-'))
        self.assertEqual(self.session.tracking_token, 'test-FOOBAR123')

    @coroutine
    def test_set_tracking_token_prefix(self):
        self.request_params['tracking_token_prefix'] = 'test-prefix-'
        yield from self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)

        self.assertTrue(self.session.tracking_token.startswith('test-prefix-'))
        self.assertEqual(len(self.session.tracking_token), 22)

    @coroutine
    def test_set_tracking_on_response(self):
        self.request_params['tracking_token_prefix'] = 'test-prefix-'
        yield from self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)
        response = yield from self.session.request()
        yield from self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertEqual(self.session.tracking_token, response.tracking_token)


class InnerLogTest(TestCase):

    def setUp(self):

        this = self

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                response = ObjectWrapper(ClientResponse('get', 'http://test.test'))
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

        self.session = ObjectWrapper(SessionMock())
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
                                    'service_name': 'test_service'}})

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
                                    'service_name': 'test_service'}})

    @coroutine
    def test_before_request_hidden_data(self):
        self.endpoint_desc['logger'] = {'hidden_request_body': True}
        self.request_params['data'] = 'data text'
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Sending request")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'REQUEST',
                                    'body': '<HIDDEN>',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service'}})

    @coroutine
    def test_before_request_stream_data(self):
        self.endpoint_desc['stream_request'] = True
        self.request_params['data'] = 'data text'
        yield from self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Sending request")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'REQUEST',
                                    'body': '<STREAM>',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service'}})

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
                                    'exception': ex}})

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
                                    'headers': resp.headers}})

    @coroutine
    def test_on_response_hidden_body(self):
        self.endpoint_desc['logger'] = {'hidden_response_body': True}
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
                                    'body': '<HIDDEN>',
                                    'elapsed': resp.elapsed,
                                    'headers': resp.headers}})

    @coroutine
    def test_on_response_stream_body(self):
        self.endpoint_desc['stream_response'] = True
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
                                    'body': '<STREAM>',
                                    'elapsed': resp.elapsed,
                                    'headers': resp.headers}})

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
                                    'exception': ex}})


class OuterLogTest(TestCase):

    def setUp(self):
        this = self

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                response = ObjectWrapper(ClientResponse('get', 'http://test.test'))
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

        self.session = ObjectWrapper(SessionMock())
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
                                    'service_name': 'test_service'}})

    @coroutine
    def test_prepare_payload_hidden_data(self):
        self.endpoint_desc['logger'] = {'hidden_request_body': True}
        yield from self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, 'aaaaa')

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Sending request")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'REQUEST',
                                    'body': '<HIDDEN>',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service'}})

    @coroutine
    def test_prepare_payload_stream_data(self):
        self.endpoint_desc['stream_request'] = True
        yield from self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, 'aaaaa')

        self.assertEqual(self.logger.level, logging.INFO)
        self.assertEqual(self.logger.message, "Sending request")
        self.assertEqual(self.logger.args, tuple())
        self.assertEqual(self.logger.kwargs,
                         {"extra": {'action': 'REQUEST',
                                    'body': '<STREAM>',
                                    'endpoint': 'test_endpoint',
                                    'path_param1': 'foo',
                                    'path_param2': 'bar',
                                    'service_name': 'test_service'}})

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
                                    'service_name': 'test_service'}})

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
                                    'exception': ex}})

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
                                    'headers': resp.headers}})

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
                                    'exception': ex}})


class PoolTest(TestCase):

    def setUp(self):
        this = self

        class SessionMock:

            @coroutine
            def request(self, *args, **kwargs):
                response = ObjectWrapper(ClientResponse('get', 'http://test.test'))
                response._post_init(this.loop)
                response._content = b'ssssssss'
                response.status = 200
                response.elapsed = timedelta(seconds=100)
                response.headers = CIMultiDict({"content-type": "application/json"})
                return response

        class ServiceMock:

            name = 'test_service'
            loop = self.loop

        self.plugin = Pool()

        self.service = ServiceMock()
        self.plugin.assign_service_client(self.service)

        self.session = ObjectWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'POST',
                              'param1': 'obladi',
                              'param2': 'oblada',
                              'endpoint': 'test_endpoint'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    @coroutine
    def test_pool_limit(self):

        fut = self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        yield from asyncio.wait_for(fut, 0.1)

        fut = self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        with self.assertRaises(TimeoutError):
            yield from asyncio.wait_for(shield(fut), 0.1)

        yield from self.plugin.on_response(self.endpoint_desc, self.session,
                                           self.request_params, None)

        yield from asyncio.wait_for(fut, 0.1)

    @coroutine
    def test_pool_limit_using_exception(self):
        fut = self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        yield from asyncio.wait_for(fut, 0.1)

        fut = self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        with self.assertRaises(TimeoutError):
            yield from asyncio.wait_for(shield(fut), 0.1)

        yield from self.plugin.on_exception(self.endpoint_desc, self.session,
                                            self.request_params, Exception())

        yield from asyncio.wait_for(fut, 0.1)
