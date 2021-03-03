'''
Created on 04/04/2014

@author: alfred
'''
import logging
from asyncio import TimeoutError
from asyncio.tasks import Task, ensure_future, gather, shield, sleep, wait, wait_for
from datetime import datetime, timedelta

try:
    all_tasks = Task.all_tasks
except AttributeError:  # pragma: no cover
    from asyncio import all_tasks

from aiohttp.client import ClientSession
from asynctest.case import TestCase
from multidict import CIMultiDict
from yarl import URL

from service_client import ConnectionClosedError
from service_client.plugins import Elapsed, Headers, InnerLogger, OuterLogger, PathTokens, Pool, \
    QueryParams, RateLimit, Timeout, TooManyRequestsPendingError, TooMuchTimePendingError, TrackingToken
from service_client.utils import ObjectWrapper
from tests import create_fake_response


class PathTests(TestCase):

    async def setUp(self):
        self.plugin = PathTokens()
        self.session = ClientSession()
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    async def test_no_changes(self):
        self.assertEqual((await self.plugin.prepare_path(self.endpoint_desc,
                                                         self.session,
                                                         self.request_params,
                                                         '/test/path/noway')),
                         '/test/path/noway')

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar'})

    async def test_one_param(self):
        self.assertEqual((await self.plugin.prepare_path(self.endpoint_desc,
                                                         self.session,
                                                         self.request_params,
                                                         '/test/{path_param1}/noway')),
                         '/test/foo/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})

    async def test_one_special_param(self):
        request_params = {'path_param1': '*'}
        self.assertEqual((await self.plugin.prepare_path(self.endpoint_desc,
                                                         self.session,
                                                         request_params,
                                                         '/test/{path_param1}/noway')),
                         '/test/%2A/noway')

        self.assertDictEqual(request_params, {})

    async def test_one_int_param(self):
        request_params = {'path_param1': 1}
        self.assertEqual((await self.plugin.prepare_path(self.endpoint_desc,
                                                         self.session,
                                                         request_params,
                                                         '/test/{path_param1}/noway')),
                         '/test/1/noway')

        self.assertDictEqual(request_params, {})

    async def test_two_params(self):
        self.assertEqual((await self.plugin.prepare_path(self.endpoint_desc,
                                                         self.session,
                                                         self.request_params,
                                                         '/test/{path_param1}/{path_param2}/noway')),
                         '/test/foo/bar/noway')

        self.assertDictEqual(self.request_params, {})

    async def test_two_params_repeated(self):
        self.assertEqual((await self.plugin.prepare_path(self.endpoint_desc,
                                                         self.session,
                                                         self.request_params,
                                                         '/test/{path_param1}/{path_param1}/noway')),
                         '/test/foo/foo/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})

    async def test_no_param(self):
        self.assertEqual((await self.plugin.prepare_path(self.endpoint_desc,
                                                         self.session,
                                                         self.request_params,
                                                         '/test/{path_param1}/{path_param3}/noway')),
                         '/test/foo/{path_param3}/noway')

        self.assertDictEqual(self.request_params, {'path_param2': 'bar'})


class ResponseMock:

    def __init__(self, spend_time):
        self.spend_time = spend_time

    async def start(self, *args, **kwargs):
        await sleep(self.spend_time)

    async def read(self):
        await sleep(self.spend_time)
        return 'data'


class TimeoutTests(TestCase):

    async def setUp(self):
        class SessionMock:
            async def request(self, *args, **kwargs):
                await sleep(0.5)
                raise Exception("No timeout")

        self.plugin = Timeout(default_timeout=0.1)
        self.session = ObjectWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    async def test_use_default(self):
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        t = datetime.now()
        with self.assertRaises(TimeoutError):
            await self.session.request()
        self.assertGreater(datetime.now() - t, timedelta(seconds=0.1))
        self.assertLess(datetime.now() - t, timedelta(seconds=0.2))

    async def test_use_service(self):
        self.endpoint_desc['timeout'] = 0.2
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        t = datetime.now()
        with self.assertRaises(TimeoutError):
            await self.session.request()
        self.assertGreater(datetime.now() - t, timedelta(seconds=0.2))
        self.assertLess(datetime.now() - t, timedelta(seconds=0.3))

    async def test_use_request(self):
        self.endpoint_desc['timeout'] = 0.2
        self.request_params['timeout'] = 0.3
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        t = datetime.now()
        with self.assertRaises(TimeoutError):
            await self.session.request()
        self.assertGreater(datetime.now() - t, timedelta(seconds=0.3))
        self.assertLess(datetime.now() - t, timedelta(seconds=0.4))

    async def test_no_timeout(self):
        self.request_params['timeout'] = None
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        with self.assertRaisesRegex(Exception, "No timeout"):
            await self.session.request()


class TimeoutWithResponseTests(TestCase):

    async def setUp(self):
        class SessionMock:
            async def request(self, *args, **kwargs):
                await sleep(0.5)
                return 'response'

        self.plugin = Timeout(default_timeout=0.1)
        self.session = ObjectWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    async def test_no_timeout(self):
        self.request_params['timeout'] = None
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

        self.assertEqual((await self.session.request()), 'response')


class HeadersTests(TestCase):

    async def setUp(self):
        self.plugin = Headers(default_headers={'x-foo-bar': 'test headers'})
        self.session = ClientSession()
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    async def test_use_default(self):
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params,
                             {'path_param1': 'foo',
                              'path_param2': 'bar',
                              'headers': CIMultiDict({'X-Foo-Bar': 'test headers'})})

    async def test_use_service(self):
        self.endpoint_desc['headers'] = {'x-foo-bar': 'test headers service_client'}
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params,
                             {'path_param1': 'foo',
                              'path_param2': 'bar',
                              'headers': CIMultiDict({'X-Foo-Bar': 'test headers service_client'})})

    async def test_add_from_service(self):
        self.endpoint_desc['headers'] = {'x-foo-bar-service': 'test headers service_client'}
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params,
                             {'path_param1': 'foo',
                              'path_param2': 'bar',
                              'headers': CIMultiDict({'X-Foo-Bar': 'test headers',
                                                      'X-Foo-Bar-Service': 'test headers service_client'})})

    async def test_use_request(self):
        self.endpoint_desc['headers'] = {'x-foo-bar': 'test headers service_client'}
        self.request_params['headers'] = {'x-foo-bar': 'test headers request'}
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params,
                             {'path_param1': 'foo',
                              'path_param2': 'bar',
                              'headers': CIMultiDict({'X-Foo-Bar': 'test headers request'})})

        async def test_add_from_request(self):
            self.endpoint_desc['headers'] = {'x-foo-bar-service': 'test headers service_client'}
            self.request_params['headers'] = {'x-foo-bar-request': 'test headers request'}
            await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

            self.assertDictEqual(self.request_params,
                                 {'path_param1': 'foo',
                                  'path_param2': 'bar',
                                  'headers': CIMultiDict({'X-Foo-Bar': 'test headers',
                                                          'X-Foo-Bar-Service': 'test headers service_client',
                                                          'X-Foo-Bar-Request': 'test headers request'})})


class QueryParamsTest(TestCase):

    async def setUp(self):
        self.plugin = QueryParams()
        self.session = ClientSession()
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada',
                              'query_params': {'qparam1': 1, 'qparam2': 'test2'}}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    async def test_use_endpoint_default(self):
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {'qparam1': 1, 'qparam2': 'test2'}})

    async def test_use_request(self):
        self.request_params['params'] = {'qparamRequest': 'test'}
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {
                                                       'qparam1': 1,
                                                       'qparam2': 'test2',
                                                       'qparamRequest': 'test'}})


class QueryParamsDefaultTest(TestCase):

    async def setUp(self):
        self.plugin = QueryParams(default_query_params={'default_param1': 'value1',
                                                        'default_param2': 'value2'})
        self.session = ClientSession()
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada',
                              'query_params': {'qparam1': 1, 'qparam2': 'test2'}}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    async def test_use_endpoint_default(self):
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {'qparam1': 1,
                                                              'qparam2': 'test2',
                                                              'default_param1': 'value1',
                                                              'default_param2': 'value2'}})

    async def test_use_endpoint_override(self):
        self.endpoint_desc['query_params'].update({'default_param1': 2,
                                                   'default_param2': 'foo'})
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {'qparam1': 1,
                                                              'qparam2': 'test2',
                                                              'default_param1': 2,
                                                              'default_param2': 'foo'}})

    async def test_use_endpoint_remove_default(self):
        self.endpoint_desc['query_params'].update({'default_param1': None,
                                                   'default_param2': 'foo'})
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {'qparam1': 1,
                                                              'qparam2': 'test2',
                                                              'default_param2': 'foo'}})

    async def test_use_request(self):
        self.request_params['params'] = {'qparamRequest': 'test'}
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params, {'path_param1': 'foo',
                                                   'path_param2': 'bar',
                                                   'params': {
                                                       'qparam1': 1,
                                                       'qparam2': 'test2',
                                                       'qparamRequest': 'test',
                                                       'default_param1': 'value1',
                                                       'default_param2': 'value2'}})

    async def test_use_request_override(self):
        self.request_params['params'] = {'qparamRequest': 'test',
                                         'default_param1': 3,
                                         'default_param2': 'bar'}
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params,
                             {'path_param1': 'foo',
                              'path_param2': 'bar',
                              'params': {
                                  'qparam1': 1,
                                  'qparam2': 'test2',
                                  'qparamRequest': 'test',
                                  'default_param1': 3,
                                  'default_param2': 'bar'}},
                             self.request_params)

    async def test_use_request_remove(self):
        self.request_params['params'] = {'qparamRequest': 'test',
                                         'default_param1': None,
                                         'default_param2': 'bar'}
        await self.plugin.prepare_request_params(self.endpoint_desc, self.session, self.request_params)

        self.assertDictEqual(self.request_params,
                             {'path_param1': 'foo',
                              'path_param2': 'bar',
                              'params': {
                                  'qparam1': 1,
                                  'qparam2': 'test2',
                                  'qparamRequest': 'test',
                                  'default_param2': 'bar'}})


class ElapsedTest(TestCase):
    spend_time = 0.1

    async def setUp(self):
        this = self

        class SessionMock:
            response = ObjectWrapper(ResponseMock(0.1))

            async def request(self, *args, **kwargs):
                await sleep(this.spend_time)
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

    async def test_headers_elapsed(self):
        response = ObjectWrapper(ResponseMock(0.1))
        self.plugin.prepare_response(self.endpoint_desc, self.session, self.request_params, response)

        t = datetime.now()
        await response.start()
        self.assertGreater(response.headers_elapsed, timedelta(seconds=0.1))
        self.assertLess(response.headers_elapsed, timedelta(seconds=0.2))
        self.assertGreater(response.start_headers, t)
        self.assertLess(response.start_headers, datetime.now())

    async def test_headers_elapsed_2(self):
        response = ObjectWrapper(ResponseMock(0.2))
        self.plugin.prepare_response(self.endpoint_desc, self.session, self.request_params, response)

        t = datetime.now()
        await response.start()
        self.assertGreater(response.headers_elapsed, timedelta(seconds=0.2))
        self.assertLess(response.headers_elapsed, timedelta(seconds=0.3))
        self.assertGreater(response.start_headers, t)
        self.assertLess(response.start_headers, datetime.now())

    async def test_no_headers_elapsed_endpoint(self):
        self.endpoint_desc['elapsed'] = {'headers': False}
        response = ObjectWrapper(ResponseMock(0.1))
        self.plugin.prepare_response(self.endpoint_desc, self.session, self.request_params, response)

        await response.start()
        self.assertFalse(hasattr(response, 'headers_elapsed'))
        self.assertFalse(hasattr(response, 'start_headers'))

    async def test_no_headers_elapsed_request_params(self):
        self.request_params['headers_elapsed'] = False
        response = ObjectWrapper(ResponseMock(0.1))
        self.plugin.prepare_response(self.endpoint_desc, self.session, self.request_params, response)

        await response.start()
        self.assertFalse(hasattr(response, 'headers_elapsed'))
        self.assertFalse(hasattr(response, 'start_headers'))

    async def test_read_elapsed(self):
        response = ObjectWrapper(ResponseMock(0.1))
        t = datetime.now()
        await self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)
        await sleep(0.1)
        await self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)

        self.assertGreater(response.read_elapsed, timedelta(seconds=0.1))
        self.assertLess(response.read_elapsed, timedelta(seconds=0.2))
        self.assertGreater(response.start_read, t)
        self.assertLess(response.start_read, datetime.now())

    async def test_read_elapsed_2(self):
        response = ObjectWrapper(ResponseMock(0.2))
        t = datetime.now()
        await self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)
        await sleep(0.2)
        await self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)

        self.assertGreater(response.read_elapsed, timedelta(seconds=0.2))
        self.assertLess(response.read_elapsed, timedelta(seconds=0.3))
        self.assertGreater(response.start_read, t)
        self.assertLess(response.start_read, datetime.now())

    async def test_no_read_elapsed_endpoint(self):
        self.endpoint_desc['elapsed'] = {'read': False}
        response = ObjectWrapper(ResponseMock(0.1))
        await self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)
        await self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)

        self.assertFalse(hasattr(response, 'read_elapsed'))
        self.assertFalse(hasattr(response, 'start_read'))

    async def test_no_read_elapsed_request_params(self):
        self.request_params['read_elapsed'] = False
        response = ObjectWrapper(ResponseMock(0.1))
        await self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)
        await self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)

        self.assertFalse(hasattr(response, 'read_elapsed'))
        self.assertFalse(hasattr(response, 'start_read'))

    async def test_parse_elapsed(self):
        response = ObjectWrapper(ResponseMock(0.1))
        t = datetime.now()
        await self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)
        await sleep(0.1)
        await self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertGreater(response.parse_elapsed, timedelta(seconds=0.1))
        self.assertLess(response.parse_elapsed, timedelta(seconds=0.2))
        self.assertGreater(response.start_parse, t)
        self.assertLess(response.start_parse, datetime.now())

    async def test_parse_elapsed_2(self):
        response = ObjectWrapper(ResponseMock(0.2))
        t = datetime.now()
        await self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)
        await sleep(0.2)
        await self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertGreater(response.parse_elapsed, timedelta(seconds=0.2))
        self.assertLess(response.parse_elapsed, timedelta(seconds=0.3))
        self.assertGreater(response.start_parse, t)
        self.assertLess(response.start_parse, datetime.now())

    async def test_no_parse_elapsed_endpoint(self):
        self.endpoint_desc['elapsed'] = {'parse': False}
        response = ObjectWrapper(ResponseMock(0.1))
        await self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)
        await self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertFalse(hasattr(response, 'parse_elapsed'))
        self.assertFalse(hasattr(response, 'start_parse'))

    async def test_no_parse_elapsed_request_params(self):
        self.request_params['parse_elapsed'] = False
        response = ObjectWrapper(ResponseMock(0.1))
        await self.plugin.on_read(self.endpoint_desc, self.session, self.request_params, response)
        await self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertFalse(hasattr(response, 'parse_elapsed'))
        self.assertFalse(hasattr(response, 'start_parse'))


class TrackingTokenTest(TestCase):

    async def setUp(self):
        this = self

        class SessionMock:
            async def request(self, *args, **kwargs):
                return ObjectWrapper(await create_fake_response('get', URL('http://test.test'),
                                                                session=self, loop=this.loop))

        self.plugin = TrackingToken(prefix='test-')
        self.session = ObjectWrapper(SessionMock())
        self.endpoint_desc = {'path': '/test1/path/noway',
                              'method': 'GET',
                              'param1': 'obladi',
                              'param2': 'oblada'}

        self.request_params = {'path_param1': 'foo',
                               'path_param2': 'bar'}

    async def test_generate_tracking_token(self):
        await self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)

        self.assertTrue(self.session.tracking_token.startswith('test-'))
        self.assertEqual(len(self.session.tracking_token), 15)

    async def test_set_tracking_token(self):
        self.request_params['tracking_token'] = 'FOOBAR123'
        await self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)

        self.assertTrue(self.session.tracking_token.startswith('test-'))
        self.assertEqual(self.session.tracking_token, 'test-FOOBAR123')

    async def test_set_tracking_token_prefix(self):
        self.request_params['tracking_token_prefix'] = 'test-prefix-'
        await self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)

        self.assertTrue(self.session.tracking_token.startswith('test-prefix-'))
        self.assertEqual(len(self.session.tracking_token), 22)

    async def test_set_tracking_on_response(self):
        self.request_params['tracking_token_prefix'] = 'test-prefix-'
        await self.plugin.prepare_session(self.endpoint_desc, self.session, self.request_params)
        response = await self.session.request()
        await self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, response)

        self.assertEqual(self.session.tracking_token, response.tracking_token)


class InnerLogTest(TestCase):

    async def setUp(self):
        this = self

        class SessionMock:
            async def request(self, *args, **kwargs):
                response = ObjectWrapper(await create_fake_response('get', URL('http://test.test'),
                                                                    session=self, loop=this.loop))

                response._body = b'ssssssss'
                response.status = 200
                response.elapsed = timedelta(seconds=100)
                response._headers = CIMultiDict({"content-type": "application/json"})
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

    async def test_before_request(self):
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

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

    async def test_before_request_with_data(self):
        self.request_params['data'] = 'data text'
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

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

    async def test_before_request_hidden_data(self):
        self.endpoint_desc['logger'] = {'hidden_request_body': True}
        self.request_params['data'] = 'data text'
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

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

    async def test_before_request_stream_data(self):
        self.endpoint_desc['stream_request'] = True
        self.request_params['data'] = 'data text'
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)

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

    async def test_on_exception(self):
        ex = AttributeError('Testing Exception')
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)
        await self.plugin.on_exception(self.endpoint_desc, self.session, self.request_params, ex)

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

    async def test_on_response(self):
        resp = await self.session.request()
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)
        await self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, resp)

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

    async def test_on_response_hidden_body(self):
        self.endpoint_desc['logger'] = {'hidden_response_body': True}
        resp = await self.session.request()
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)
        await self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, resp)

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

    async def test_on_response_stream_body(self):
        self.endpoint_desc['stream_response'] = True
        resp = await self.session.request()
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)
        await self.plugin.on_response(self.endpoint_desc, self.session, self.request_params, resp)

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

    async def test_on_parse_exception(self):
        ex = AttributeError('Testing Exception')
        resp = await self.session.request()
        await self.plugin.before_request(self.endpoint_desc, self.session, self.request_params)
        await self.plugin.on_parse_exception(self.endpoint_desc, self.session, self.request_params, resp, ex)

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

    async def setUp(self):
        this = self

        class SessionMock:
            async def request(self, *args, **kwargs):
                response = ObjectWrapper(await create_fake_response('get', URL('http://test.test'),
                                                                    session=self, loop=this.loop))

                response._body = b'ssssssss'
                response.status = 200
                response.elapsed = timedelta(seconds=100)
                response._headers = CIMultiDict({"content-type": "application/json"})
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

    async def test_prepare_payload(self):
        await self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, 'aaaaa')

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

    async def test_prepare_payload_hidden_data(self):
        self.endpoint_desc['logger'] = {'hidden_request_body': True}
        await self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, 'aaaaa')

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

    async def test_prepare_payload_stream_data(self):
        self.endpoint_desc['stream_request'] = True
        await self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, 'aaaaa')

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

    async def test_prepare_payload_with_no_data(self):
        await self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, None)

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

    async def test_on_exception(self):
        ex = AttributeError('Testing Exception')
        await self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, None)
        await self.plugin.on_exception(self.endpoint_desc, self.session, self.request_params, ex)

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

    async def test_on_parse_response(self):
        resp = await self.session.request()
        resp.data = 'bbbbb'
        await self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, None)
        await self.plugin.on_parsed_response(self.endpoint_desc, self.session, self.request_params, resp)

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

    async def test_on_parse_exception(self):
        ex = AttributeError('Testing Exception')
        resp = await self.session.request()
        await self.plugin.prepare_payload(self.endpoint_desc, self.session, self.request_params, None)
        await self.plugin.on_parse_exception(self.endpoint_desc, self.session, self.request_params, resp, ex)

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

    async def setUp(self):
        this = self

        class SessionMock:
            async def request(self, *args, **kwargs):
                response = ObjectWrapper(await create_fake_response('get', URL('http://test.test'),
                                                                    session=self, loop=this.loop))
                response._body = b'ssssssss'
                response.status = 200
                response.elapsed = timedelta(seconds=100)
                response.headers = CIMultiDict({"content-type": "application/json"})
                return response

        class ServiceMock:
            name = 'test_service'
            loop = self.loop

        self.plugin = Pool(limit=1, timeout=0.1, hard_limit=1)

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

    def tearDown(self):
        pending = [t for t in all_tasks(loop=self.loop) if not t.done()]
        while len(pending):
            try:
                self.loop.run_until_complete(gather(*pending,
                                                    loop=self.loop))
            except BaseException:
                pass
            finally:
                pending = [t for t in all_tasks(loop=self.loop) if not t.done()]

    async def test_limit(self):
        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        fut = ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                       self.request_params))

        with self.assertRaises(TimeoutError):
            await wait_for(shield(fut), 0.01)

        await self.plugin.on_response(self.endpoint_desc, self.session,
                                      self.request_params, None)

        await wait_for(fut, 0.1)

    async def test_limit_using_exception(self):
        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        fut = ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                       self.request_params))

        with self.assertRaises(TimeoutError):
            await wait_for(shield(fut), 0.01)

        await self.plugin.on_exception(self.endpoint_desc, self.session,
                                       self.request_params, Exception())

        await wait_for(fut, 0.1)

    async def test_timeout(self):
        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        with self.assertRaisesRegex(TooMuchTimePendingError, "Request blocked too much time on pool"):
            await self.plugin.before_request(self.endpoint_desc, self.session,
                                             self.request_params)

        self.assertGreaterEqual(self.session.blocked_by_pool, 0.1)
        self.assertLessEqual(self.session.blocked_by_pool, 0.5)

    async def test_hard_limit(self):
        ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                 self.request_params))
        ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                 self.request_params))
        ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                 self.request_params))

        with self.assertRaisesRegex(TooManyRequestsPendingError, "Too many requests pending on pool"):
            await wait_for(self.plugin.before_request(self.endpoint_desc, self.session,
                                                      self.request_params), timeout=1)

        self.assertGreaterEqual(self.session.blocked_by_pool, 0)
        self.assertLessEqual(self.session.blocked_by_pool, 0.1)

    async def test_close(self):
        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        with self.assertRaises(ConnectionClosedError):
            fut = ensure_future(self.plugin.before_request(self.endpoint_desc,
                                                           self.session,
                                                           self.request_params))
            await sleep(0)
            self.plugin.close()
            await fut

    async def test_regular_work(self):
        for _ in range(10):
            await self.plugin.before_request(self.endpoint_desc, self.session,
                                             self.request_params)

            await self.plugin.on_response(self.endpoint_desc, self.session,
                                          self.request_params, None)


class RateLimitTest(TestCase):

    async def setUp(self):
        this = self

        class SessionMock:
            async def request(self, *args, **kwargs):
                response = ObjectWrapper(await create_fake_response('get', URL('http://test.test'),
                                                                    session=self, loop=this.loop))
                response._body = b'ssssssss'
                response.status = 200
                response.elapsed = timedelta(seconds=100)
                response.headers = CIMultiDict({"content-type": "application/json"})
                return response

        class ServiceMock:
            name = 'test_service'
            loop = self.loop

        self.plugin = RateLimit(limit=1, period=0.2, timeout=0.5, hard_limit=1)

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

    def tearDown(self):
        pending = [t for t in all_tasks(loop=self.loop) if not t.done()]
        while len(pending):
            try:
                self.loop.run_until_complete(gather(*pending,
                                                    loop=self.loop))
            except BaseException:
                pass
            finally:
                pending = [t for t in all_tasks(loop=self.loop) if not t.done()]

    async def test_limit(self):
        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        fut = ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                       self.request_params))

        with self.assertRaises(TimeoutError):
            await wait_for(shield(fut), 0.1)

        await self.plugin.on_response(self.endpoint_desc, self.session,
                                      self.request_params, None)

        await sleep(0.2)

        await wait_for(fut, 0.5)

    async def test_limit_using_exception(self):
        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        fut = ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                       self.request_params))

        with self.assertRaises(TimeoutError):
            await wait_for(shield(fut), 0.1)

        await self.plugin.on_exception(self.endpoint_desc, self.session,
                                       self.request_params, Exception())

        await sleep(0.2)

        await wait_for(fut, 0.1)

    async def test_timeout(self):
        await wait([
            ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                     self.request_params)),
            ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                     self.request_params))
        ])

        await self.plugin.on_exception(self.endpoint_desc, self.session,
                                       self.request_params, Exception())

        await sleep(0.2)

        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        with self.assertRaisesRegex(TooMuchTimePendingError, "Request blocked too much time by rate limit"):
            await self.plugin.before_request(self.endpoint_desc, self.session,
                                             self.request_params)

        self.assertGreaterEqual(self.session.blocked_by_ratelimit, 0.5)
        self.assertLessEqual(self.session.blocked_by_ratelimit, 1)

    async def test_hard_limit(self):
        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)
        ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                 self.request_params))
        ensure_future(self.plugin.before_request(self.endpoint_desc, self.session,
                                                 self.request_params))

        with self.assertRaisesRegex(TooManyRequestsPendingError, "Too many requests pending by rate limit"):
            await wait_for(self.plugin.before_request(self.endpoint_desc, self.session,
                                                      self.request_params), timeout=1)

        self.assertGreaterEqual(self.session.blocked_by_ratelimit, 0)
        self.assertLessEqual(self.session.blocked_by_ratelimit, 0.5)

    async def test_close(self):
        await self.plugin.before_request(self.endpoint_desc, self.session,
                                         self.request_params)

        with self.assertRaises(ConnectionClosedError):
            fut = ensure_future(self.plugin.before_request(self.endpoint_desc,
                                                           self.session,
                                                           self.request_params))
            await sleep(0)
            self.plugin.close()
            await fut

    async def test_regular_work(self):
        for _ in range(10):
            await self.plugin.before_request(self.endpoint_desc, self.session,
                                             self.request_params)

            await self.plugin.on_response(self.endpoint_desc, self.session,
                                          self.request_params, None)

            await sleep(0.2)
