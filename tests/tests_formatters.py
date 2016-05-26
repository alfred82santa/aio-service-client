import logging
from collections import OrderedDict
from unittest.case import TestCase

from datetime import timedelta

from service_client.formatters import ServiceClientFormatter


class ServiceClientFormatterTest(TestCase):

    def setUp(self):

        self.formatter = ServiceClientFormatter(fmt='%(action)s | %(method)s %(full_url)s',
                                                request_fmt='\nHeaders:\n%(headers)s\nBody:\n%(body)s',
                                                response_fmt=' | %(status_code)s %(status_text)s | %(elapsed)s'
                                                             '\nHeaders:\n%(headers)s\nBody:\n%(body)s',
                                                exception_fmt=' | %(exception_repr)s',
                                                parse_exception_fmt=' | %(status_code)s %(status_text)s | %(elapsed)s'
                                                                    ' | %(exception_repr)s'
                                                                    '\nHeaders:\n%(headers)s\nBody:\n%(body)s',
                                                headers_fmt='%(name)s: %(value)s',
                                                headers_sep='\n')

        self.logger = logging.getLogger('test')

    def test_request(self):

        log_entry = self.logger.makeRecord('test', logging.INFO, 'test_request', 22, 'Test Message', tuple(), None,
                                           extra={'action': 'REQUEST',
                                                  'method': 'GET',
                                                  'url': 'http://example.com',
                                                  'headers': OrderedDict([('Test-Header-1', 'header value 1'),
                                                                          ('Test-Header-2', 'header value 2')]),
                                                  'body': 'foobar'})
        log_text = """REQUEST | GET http://example.com
Headers:
Test-Header-1: header value 1
Test-Header-2: header value 2
Body:
foobar"""

        self.assertEqual(self.formatter.formatMessage(log_entry), log_text)

    def test_response(self):

        log_entry = self.logger.makeRecord('test', logging.INFO, 'test_request', 22, 'Test Message', tuple(), None,
                                           extra={'action': 'RESPONSE',
                                                  'method': 'GET',
                                                  'url': 'http://example.com',
                                                  'params': OrderedDict([('query_param_1', 'value_1'),
                                                                         ('query_param_2', 'value_2')]),
                                                  'headers': OrderedDict([('Test-Header-1', 'header value 1'),
                                                                          ('Test-Header-2', 'header value 2')]),
                                                  'body': 'foobar',
                                                  'status_code': 404,
                                                  'elapsed': timedelta(seconds=0.214)})
        log_text = """RESPONSE | GET http://example.com?query_param_1=value_1&query_param_2=value_2 | 404 Not Found | 214 ms
Headers:
Test-Header-1: header value 1
Test-Header-2: header value 2
Body:
foobar"""

        self.assertEqual(self.formatter.formatMessage(log_entry), log_text)

    def test_response_unknown_code(self):
        log_entry = self.logger.makeRecord('test', logging.INFO, 'test_request', 22, 'Test Message', tuple(), None,
                                           extra={'action': 'RESPONSE',
                                                  'method': 'GET',
                                                  'url': 'http://example.com',
                                                  'headers': OrderedDict([('Test-Header-1', 'header value 1'),
                                                                          ('Test-Header-2', 'header value 2')]),
                                                  'body': 'foobar',
                                                  'status_code': 1004,
                                                  'elapsed': timedelta(seconds=0.214)})
        log_text = """RESPONSE | GET http://example.com | 1004 Unknown | 214 ms
Headers:
Test-Header-1: header value 1
Test-Header-2: header value 2
Body:
foobar"""

        self.assertEqual(self.formatter.formatMessage(log_entry), log_text)

    def test_on_parse_exception(self):

        log_entry = self.logger.makeRecord('test', logging.CRITICAL, 'test_request', 22, 'Test Message', tuple(), None,
                                           extra={'action': 'EXCEPTION',
                                                  'method': 'GET',
                                                  'url': 'http://example.com',
                                                  'headers': OrderedDict([('Test-Header-1', 'header value 1'),
                                                                          ('Test-Header-2', 'header value 2')]),
                                                  'body': 'foobar',
                                                  'status_code': 404,
                                                  'elapsed': timedelta(seconds=0.214),
                                                  'exception': AttributeError('test exception')})
        log_text = """EXCEPTION | GET http://example.com | 404 Not Found | 214 ms | AttributeError('test exception',)
Headers:
Test-Header-1: header value 1
Test-Header-2: header value 2
Body:
foobar"""

        self.assertEqual(self.formatter.formatMessage(log_entry), log_text)

    def test_on_exception(self):
        log_entry = self.logger.makeRecord('test', logging.INFO, 'test_request', 22, 'Test Message', tuple(), None,
                                           extra={'action': 'EXCEPTION',
                                                  'method': 'GET',
                                                  'url': 'http://example.com',
                                                  'exception': AttributeError('test exception')})
        log_text = "EXCEPTION | GET http://example.com | AttributeError('test exception',)"

        self.assertEqual(self.formatter.formatMessage(log_entry), log_text)

    def test_unknown_action(self):
        log_entry = self.logger.makeRecord('test', logging.INFO, 'test_request', 22, 'Test Message', tuple(), None,
                                           extra={'action': 'UNKNOWN',
                                                  'method': 'GET',
                                                  'url': 'http://example.com',
                                                  'exception': AttributeError('test exception')})
        log_text = "UNKNOWN | GET http://example.com"

        self.assertEqual(self.formatter.formatMessage(log_entry), log_text)
