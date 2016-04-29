from asyncio.coroutines import coroutine
from aiohttp.client_reqrep import ClientResponse
from asynctest.case import TestCase
from asynctest.mock import patch
from service_client import ServiceClient


class FakePlugin:

    def __init__(self):
        self.calls = {}

    def assign_service_client(self, *args, **kwargs):
        self.calls['assign_service_client'] = {'args': args, 'kwargs': kwargs}

    @coroutine
    def prepare_session(self, *args, **kwargs):
        self.calls['prepare_session'] = {'args': args, 'kwargs': kwargs}
        self.session = kwargs['session']

    @coroutine
    def prepare_path(self, *args, **kwargs):
        self.calls['prepare_path'] = {'args': args, 'kwargs': kwargs}
        return kwargs['path']

    @coroutine
    def prepare_request_params(self, *args, **kwargs):
        self.calls['prepare_request_params'] = {'args': args, 'kwargs': kwargs}

    @coroutine
    def prepare_payload(self, *args, **kwargs):
        self.calls['prepare_payload'] = {'args': args, 'kwargs': kwargs}
        return kwargs['payload']

    @coroutine
    def before_request(self, *args, **kwargs):
        self.calls['before_request'] = {'args': args, 'kwargs': kwargs}

    @coroutine
    def on_exception(self, *args, **kwargs):
        self.calls['on_exception'] = {'args': args, 'kwargs': kwargs}

    @coroutine
    def on_response(self, *args, **kwargs):
        self.calls['on_response'] = {'args': args, 'kwargs': kwargs}

    @coroutine
    def on_parse_exception(self, *args, **kwargs):
        self.calls['on_parse_exception'] = {'args': args, 'kwargs': kwargs}

    @coroutine
    def on_parsed_response(self, *args, **kwargs):
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

        self.service_client = ServiceClient(rest_service_name="TestService", spec=self.spec,
                                            plugins=[self.plugin], config=self.config,
                                            base_path='http://foo.com/sdsd')

    def tearDown(self):
        pass

    def _mock_session(self):
        @coroutine
        def request(*args, **kwargs):
            self.request = {'args': args, 'kwargs': kwargs}
            self.response = ClientResponse('get', 'http://test.test')
            self.response._post_init(self.loop)
            self.response._content = b'bbbb'
            return self.response

        self.mock_session.request.side_effect = request
        self.mock_session.return_value = self.mock_session

    @coroutine
    def test_workflow_get(self):
        response = yield from self.service_client.call('testService1')
        self.assertEqual(response, self.response)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
                             'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'service_desc': {'path': '/path/to/service1',
                                 'method': 'get',
                                 'service_name': 'testService1'},
                'session': self.mock_session,
                'request_params': {'method': 'GET',
                                   'url': 'http://foo.com/sdsd/path/to/service1'}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'service_desc': {'path': '/path/to/service1',
                                               'method': 'get',
                                               'service_name': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': 'http://foo.com/sdsd/path/to/service1'},
                              'path': 'http://foo.com/sdsd/path/to/service1'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'service_desc': {'path': '/path/to/service1',
                                               'method': 'get',
                                               'service_name': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': 'http://foo.com/sdsd/path/to/service1'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'service_desc': {'path': '/path/to/service1',
                                               'method': 'get',
                                               'service_name': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': 'http://foo.com/sdsd/path/to/service1'},
                              'payload': None})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'service_desc': {'path': '/path/to/service1',
                                               'method': 'get',
                                               'service_name': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': 'http://foo.com/sdsd/path/to/service1'}})

        self.assertIn('on_response', self.plugin.calls, "On response call")
        self.assertEqual(self.plugin.calls['on_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_response']['kwargs'],
                             {'service_desc': {'path': '/path/to/service1',
                                               'method': 'get',
                                               'service_name': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': 'http://foo.com/sdsd/path/to/service1'},
                              'response': self.response})

        self.assertIn('on_parsed_response', self.plugin.calls, "On parse response call")
        self.assertEqual(self.plugin.calls['on_parsed_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_parsed_response']['kwargs'],
                             {'service_desc': {'path': '/path/to/service1',
                                               'method': 'get',
                                               'service_name': 'testService1'},
                              'session': self.mock_session,
                              'request_params': {'method': 'GET',
                                                 'url': 'http://foo.com/sdsd/path/to/service1'},
                              'response': self.response})

        self.assertNotIn('on_exception', self.plugin.calls, "On exception call")
        self.assertNotIn('on_parse_exception', self.plugin.calls, "On parse exception call")

    @coroutine
    def test_workflow_post(self):

        response = yield from self.service_client.call('testService2', payload='aaaa')
        self.assertEqual(response, self.response)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
                             'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'service_desc': {'path': '/path/to/service2',
                                 'method': 'post',
                                 'service_name': 'testService2'},
                'session': self.mock_session,
                'request_params': {'data': 'aaaa',
                                   'method': 'POST',
                                   'url': 'http://foo.com/sdsd/path/to/service2'}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'path': 'http://foo.com/sdsd/path/to/service2'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'payload': 'aaaa'})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'}})

        self.assertIn('on_response', self.plugin.calls, "On response call")
        self.assertEqual(self.plugin.calls['on_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_response']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertIn('on_parsed_response', self.plugin.calls, "On parse response call")
        self.assertEqual(self.plugin.calls['on_parsed_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_parsed_response']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertEqual(self.response.data, b'bbbb')

        self.assertNotIn('on_exception', self.plugin.calls, "On exception call")
        self.assertNotIn('on_parse_exception', self.plugin.calls, "On parse exception call")

    @coroutine
    def test_workflow_post_direct_call(self):
        response = yield from self.service_client.testService2(payload='aaaa')
        self.assertEqual(response, self.response)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
            'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'service_desc': {'path': '/path/to/service2',
                                 'method': 'post',
                                 'service_name': 'testService2'},
                'session': self.mock_session,
                'request_params': {'data': 'aaaa',
                                   'method': 'POST',
                                   'url': 'http://foo.com/sdsd/path/to/service2'}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'path': 'http://foo.com/sdsd/path/to/service2'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'payload': 'aaaa'})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'}})

        self.assertIn('on_response', self.plugin.calls, "On response call")
        self.assertEqual(self.plugin.calls['on_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_response']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertIn('on_parsed_response', self.plugin.calls, "On parse response call")
        self.assertEqual(self.plugin.calls['on_parsed_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_parsed_response']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertEqual(self.response.data, b'bbbb')

        self.assertNotIn('on_exception', self.plugin.calls, "On exception call")
        self.assertNotIn('on_parse_exception', self.plugin.calls, "On parse exception call")

    @coroutine
    def test_workflow_post_exception_response(self):

        @coroutine
        def request(*args, **kwargs):
            self.request = {'args': args, 'kwargs': kwargs}
            self.ex = Exception()
            raise self.ex

        self.mock_session.request.side_effect = request

        with self.assertRaises(Exception) as ex:
            yield from self.service_client.call('testService2', payload='aaaa')

        self.assertEqual(self.ex, ex.exception)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
                             'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'service_desc': {'path': '/path/to/service2',
                                 'method': 'post',
                                 'service_name': 'testService2'},
                'session': self.mock_session,
                'request_params': {'data': 'aaaa',
                                   'method': 'POST',
                                   'url': 'http://foo.com/sdsd/path/to/service2'}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'path': 'http://foo.com/sdsd/path/to/service2'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'payload': 'aaaa'})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'}})

        self.assertIn('on_exception', self.plugin.calls, "On exception call")
        self.assertEqual(self.plugin.calls['on_exception']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_exception']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'ex': self.ex})

        self.assertNotIn('on_response', self.plugin.calls, "On response call")
        self.assertNotIn('on_parsed_response', self.plugin.calls, "On parsed response call")
        self.assertNotIn('on_parse_exception', self.plugin.calls, "On parse exception call")

    @coroutine
    def test_workflow_post_exception_parser(self):

        def parse(data, *args, **kwargs):
            self.ex = Exception()
            raise self.ex

        self.service_client.parser = parse

        with self.assertRaises(Exception) as ex:
            yield from self.service_client.call('testService2', payload='aaaa')
        self.assertEqual(self.ex, ex.exception)

        self.assertIn('assign_service_client', self.plugin.calls, "Assign service_client call")
        self.assertEqual(self.plugin.calls['assign_service_client']['args'], ())
        self.assertDictEqual(self.plugin.calls['assign_service_client'][
                             'kwargs'], {'service_client': self.service_client})

        self.assertIn('prepare_session', self.plugin.calls, "Prepare session call")
        self.assertEqual(self.plugin.calls['prepare_session']['args'], ())
        self.assertDictEqual(
            self.plugin.calls['prepare_session']['kwargs'], {
                'service_desc': {'path': '/path/to/service2',
                                 'method': 'post',
                                 'service_name': 'testService2'},
                'session': self.mock_session,
                'request_params': {'data': 'aaaa',
                                   'method': 'POST',
                                   'url': 'http://foo.com/sdsd/path/to/service2'}})

        self.assertIn('prepare_path', self.plugin.calls, "Prepare path call")
        self.assertEqual(self.plugin.calls['prepare_path']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_path']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'path': 'http://foo.com/sdsd/path/to/service2'})

        self.assertIn('prepare_request_params', self.plugin.calls, "Prepare request params call")
        self.assertEqual(self.plugin.calls['prepare_request_params']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_request_params']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'}})

        self.assertIn('prepare_payload', self.plugin.calls, "Prepare request payload call")
        self.assertEqual(self.plugin.calls['prepare_payload']['args'], ())
        self.assertDictEqual(self.plugin.calls['prepare_payload']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'payload': 'aaaa'})

        self.assertIn('before_request', self.plugin.calls, "Before request call")
        self.assertEqual(self.plugin.calls['before_request']['args'], ())
        self.assertDictEqual(self.plugin.calls['before_request']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'}})

        self.assertIn('on_response', self.plugin.calls, "On response call")
        self.assertEqual(self.plugin.calls['on_response']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_response']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'response': self.response})

        self.assertIn('on_parse_exception', self.plugin.calls, "On parse exception call")
        self.assertEqual(self.plugin.calls['on_parse_exception']['args'], ())
        self.assertDictEqual(self.plugin.calls['on_parse_exception']['kwargs'],
                             {'service_desc': {'path': '/path/to/service2',
                                               'method': 'post',
                                               'service_name': 'testService2'},
                              'session': self.mock_session,
                              'request_params': {'method': 'POST',
                                                 'url': 'http://foo.com/sdsd/path/to/service2',
                                                 'data': 'aaaa'},
                              'response': self.response,
                              'ex': self.ex})

        self.assertNotIn('on_exception', self.plugin.calls, "On exception call")
        self.assertNotIn('on_parsed_response', self.plugin.calls, "On parse response call")

    @coroutine
    def test_workflow_stream_response(self):
        def parse(data, *args, **kwargs):
            self.ex = Exception()
            raise self.ex

        self.service_client.parser = parse

        response = yield from self.service_client.call('testService4', payload='aaaa')
        self.assertFalse(hasattr(response, 'data'))

    @coroutine
    def test_workflow_stream_request(self):

        def serializer(data, *args, **kwargs):
            self.ex = Exception()
            raise self.ex

        self.service_client.serializer = serializer

        yield from self.service_client.call('testService5', payload='aaaa')
