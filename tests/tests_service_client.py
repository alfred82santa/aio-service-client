from asyncio.tasks import Task

from aiohttp import RequestInfo
from asynctest.case import TestCase
from asynctest.mock import patch
from yarl import URL

from service_client import ServiceClient
from service_client.utils import ObjectWrapper
from tests import create_fake_response


class FakePlugin:

    def __init__(self):
        self.calls = {}

    def assign_service_client(self, *args, **kwargs):
        self.calls['assign_service_client'] = {'args': args, 'kwargs': kwargs}

    def prepare_response(self, *args, **kwargs):
        self.calls['prepare_response'] = {'args': args, 'kwargs': kwargs}
        self.session = kwargs['session']

    async def prepare_session(self, *args, **kwargs):
        self.calls['prepare_session'] = {'args': args, 'kwargs': kwargs}
        self.session = kwargs['session']

    async def prepare_path(self, *args, **kwargs):
        self.calls['prepare_path'] = {'args': args, 'kwargs': kwargs}
        return kwargs['path']

    async def prepare_request_params(self, *args, **kwargs):
        self.calls['prepare_request_params'] = {'args': args, 'kwargs': kwargs}

    async def prepare_payload(self, *args, **kwargs):
        self.calls['prepare_payload'] = {'args': args, 'kwargs': kwargs}
        return kwargs['payload']

    async def before_request(self, *args, **kwargs):
        self.calls['before_request'] = {'args': args, 'kwargs': kwargs}

    async def on_exception(self, *args, **kwargs):
        self.calls['on_exception'] = {'args': args, 'kwargs': kwargs}

    async def on_response(self, *args, **kwargs):
        self.calls['on_response'] = {'args': args, 'kwargs': kwargs}

    async def on_read(self, *args, **kwargs):
        self.calls['on_read'] = {'args': args, 'kwargs': kwargs}

    async def on_parse_exception(self, *args, **kwargs):
        self.calls['on_parse_exception'] = {'args': args, 'kwargs': kwargs}

    async def on_parsed_response(self, *args, **kwargs):
        self.calls['on_parsed_response'] = {'args': args, 'kwargs': kwargs}


class ServiceBasicTest(TestCase):

    @patch('service_client.ClientSession')
    def setUp(self, mock_session):
        self.mock_session = mock_session
        self._mock_session()

        self.config = {}
        self.spec = {
            'testService1': {
                'path': '/path/to/service1',
                'method': 'get'
            },
            'testService2': {
                'path': '/path/to/service2',
                'method': 'post'
            },
            'testService3': {
                'path': '/path/to/service3',
                'method': 'put'
            },
            'testService4': {
                'path': '/path/to/service4',
                'method': 'get',
                'stream_response': True
            },
            'testService5': {
                'path': '/path/to/service5',
                'method': 'post',
                'stream_request': True
            }
        }

        self.plugin = FakePlugin()

        self.service_client = ServiceClient(name="TestService", spec=self.spec,
                                            plugins=[self.plugin], config=self.config,
                                            base_path='http://foo.com/sdsd')

    async def tearDown(self):
        self.service_client.close()

    def _mock_session(self):
        async def request(*args, **kwargs):
            self.request = {'args': args, 'kwargs': kwargs}
            self.response = await create_fake_response('get', 'http://test.test', session=self.mock_session)
            self.response._body = b'bbbb'
            return self.response

        async def close():
            pass

        self.mock_session.request.side_effect = request
        self.mock_session.close.side_effect = close
        self.mock_session.return_value = self.mock_session
        self.mock_session.closed = True

    async def test_workflow_get(self):
        response = await self.service_client.call('testService1')
        self.assertEqual(response, self.response)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
            'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'endpoint_desc': {'path': '/path/to/service1',
                                  'method': 'get',
                                  'endpoint': 'testService1'},
                'session': self.mock_session,
                'request_params': {'method': 'GET',
                                   'url': URL('http://foo.com/sdsd/path/to/service1')}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service1',
                                                'method': 'get',
                                                'endpoint': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': URL('http://foo.com/sdsd/path/to/service1')},
                              'path': 'http://foo.com/sdsd/path/to/service1'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service1',
                                                'method': 'get',
                                                'endpoint': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': URL('http://foo.com/sdsd/path/to/service1')}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service1',
                                                'method': 'get',
                                                'endpoint': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': URL('http://foo.com/sdsd/path/to/service1')},
                              'payload': None})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service1',
                                                'method': 'get',
                                                'endpoint': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': URL('http://foo.com/sdsd/path/to/service1')}})

        self.assertIn('on_response', self.plugin.calls, "On response call")
        self.assertEqual(self.plugin.calls['on_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_response']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service1',
                                                'method': 'get',
                                                'endpoint': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': URL('http://foo.com/sdsd/path/to/service1')},
                              'response': self.response})

        self.assertIn('on_parsed_response', self.plugin.calls, "On parse response call")
        self.assertEqual(self.plugin.calls['on_parsed_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_parsed_response']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service1',
                                                'method': 'get',
                                                'endpoint': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': URL('http://foo.com/sdsd/path/to/service1')},
                              'response': self.response})

        self.assertNotIn('on_exception', self.plugin.calls, "On exception call")
        self.assertNotIn('on_parse_exception', self.plugin.calls, "On parse exception call")

    async def test_workflow_post(self):
        response = await self.service_client.call('testService2', payload='aaaa')
        self.assertEqual(response, self.response)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
            'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'endpoint_desc': {'path': '/path/to/service2',
                                  'method': 'post',
                                  'endpoint': 'testService2'},
                'session': self.mock_session,
                'request_params': {'data': 'aaaa',
                                   'method': 'POST',
                                   'url': URL('http://foo.com/sdsd/path/to/service2')}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'path': 'http://foo.com/sdsd/path/to/service2'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'payload': 'aaaa'})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'}})

        self.assertIn('on_response', self.plugin.calls, "On response call")
        self.assertEqual(self.plugin.calls['on_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_response']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertIn('on_parsed_response', self.plugin.calls, "On parse response call")
        self.assertEqual(self.plugin.calls['on_parsed_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_parsed_response']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertEqual(self.response.data, b'bbbb')

        self.assertNotIn('on_exception', self.plugin.calls, "On exception call")
        self.assertNotIn('on_parse_exception', self.plugin.calls, "On parse exception call")

    async def test_workflow_post_direct_call(self):
        response = await self.service_client.testService2(payload='aaaa')
        self.assertEqual(response, self.response)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
            'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'endpoint_desc': {'path': '/path/to/service2',
                                  'method': 'post',
                                  'endpoint': 'testService2'},
                'session': self.mock_session,
                'request_params': {'data': 'aaaa',
                                   'method': 'POST',
                                   'url': URL('http://foo.com/sdsd/path/to/service2')}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'path': 'http://foo.com/sdsd/path/to/service2'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'payload': 'aaaa'})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'}})

        self.assertIn('on_response', self.plugin.calls, "On response call")
        self.assertEqual(self.plugin.calls['on_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_response']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertIn('on_parsed_response', self.plugin.calls, "On parse response call")
        self.assertEqual(self.plugin.calls['on_parsed_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_parsed_response']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertEqual(self.response.data, b'bbbb')

        self.assertNotIn('on_exception', self.plugin.calls, "On exception call")
        self.assertNotIn('on_parse_exception', self.plugin.calls, "On parse exception call")

    async def test_workflow_post_exception_response(self):
        async def request(*args, **kwargs):
            self.request = {'args': args, 'kwargs': kwargs}
            self.ex = Exception()
            raise self.ex

        self.mock_session.request.side_effect = request

        with self.assertRaises(Exception) as ex:
            await self.service_client.call('testService2', payload='aaaa')

        self.assertEqual(self.ex, ex.exception)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
            'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'endpoint_desc': {'path': '/path/to/service2',
                                  'method': 'post',
                                  'endpoint': 'testService2'},
                'session': self.mock_session,
                'request_params': {'data': 'aaaa',
                                   'method': 'POST',
                                   'url': URL('http://foo.com/sdsd/path/to/service2')}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'path': 'http://foo.com/sdsd/path/to/service2'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'payload': 'aaaa'})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'}})

        self.assertIn('on_exception', self.plugin.calls, "On exception call")
        self.assertEqual(self.plugin.calls['on_exception']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_exception']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'ex': self.ex})

        self.assertNotIn('on_response', self.plugin.calls, "On response call")
        self.assertNotIn('on_parsed_response', self.plugin.calls, "On parsed response call")
        self.assertNotIn('on_parse_exception', self.plugin.calls, "On parse exception call")

    async def test_workflow_post_exception_parser(self):
        def parse(data, *args, **kwargs):
            self.ex = Exception()
            raise self.ex

        self.service_client.parser = parse

        with self.assertRaises(Exception) as ex:
            await self.service_client.call('testService2', payload='aaaa')
        self.assertEqual(self.ex, ex.exception)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
            'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'endpoint_desc': {'path': '/path/to/service2',
                                  'method': 'post',
                                  'endpoint': 'testService2'},
                'session': self.mock_session,
                'request_params': {'data': 'aaaa',
                                   'method': 'POST',
                                   'url': URL('http://foo.com/sdsd/path/to/service2')}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'path': 'http://foo.com/sdsd/path/to/service2'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'payload': 'aaaa'})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'}})

        self.assertIn('on_response', self.plugin.calls, "On response call")
        self.assertEqual(self.plugin.calls['on_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_response']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertIn('on_parse_exception', self.plugin.calls, "On parse exception call")
        self.assertEqual(self.plugin.calls['on_parse_exception']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_parse_exception']['kwargs'],
                             {'endpoint_desc': {'path': '/path/to/service2',
                                                'method': 'post',
                                                'endpoint': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': URL('http://foo.com/sdsd/path/to/service2'),
                                                 'data': 'aaaa'},
                              'response': self.response,
                              'ex': self.ex})

        self.assertNotIn('on_exception', self.plugin.calls, "On exception call")
        self.assertNotIn('on_parsed_response', self.plugin.calls, "On parse response call")

    async def test_workflow_stream_response(self):
        def parse(data, *args, **kwargs):
            self.ex = Exception()
            raise self.ex

        self.service_client.parser = parse

        response = await self.service_client.call('testService4', payload='aaaa')
        self.assertFalse(hasattr(response, 'data'))

    async def test_workflow_stream_request(self):
        def serializer(data, *args, **kwargs):
            self.ex = Exception()
            raise self.ex

        self.service_client.serializer = serializer

        await self.service_client.call('testService5', payload='aaaa')

    async def test_create_response(self):
        task = Task.current_task(loop=self.loop)
        task.session = {}
        task.endpoint_desc = {}
        task.request_params = {}
        response = self.service_client.create_response(method='get', url=URL("http://test.com"),
                                                       writer=None, continue100=False, timer=None,
                                                       request_info=RequestInfo(URL("http://test.com"), 'get', []),
                                                       auto_decompress=False,
                                                       traces=[], loop=self.loop, session=self.service_client.session)
        self.assertIsInstance(response, ObjectWrapper)
