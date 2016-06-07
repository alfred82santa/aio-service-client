from logging import getLogger, NullHandler
from unittest.case import TestCase

from dirty_loader import LoaderNamespace
from dirty_loader.factories import register_logging_factories

from service_client import ServiceClient
from service_client.factories import register_service_client_factories
from service_client.json import json_decoder, json_encoder
from service_client.plugins import InnerLogger, PathTokens


class LoggerPluginFactoryFactoryTests(TestCase):

    def setUp(self):
        self.loader = LoaderNamespace()
        self.loader.register_namespace('logging', 'logging')
        self.loader.register_namespace('sc-plugins', 'service_client.plugins')
        register_logging_factories(self.loader)
        register_service_client_factories(self.loader)

    def test_inner_logger_build(self):
        plugin = self.loader.factory('sc-plugins:InnerLogger', logger={'type': 'logging:Logger',
                                                                       'params': {'name': 'foo.bar.test.1',
                                                                                  'handlers': ['logging:NullHandler']}})
        self.assertIsInstance(plugin, InnerLogger)
        self.assertEqual(plugin.logger, getLogger('foo.bar.test.1'))
        self.assertEqual(len(plugin.logger.handlers), 1)
        self.assertIsInstance(plugin.logger.handlers[0], NullHandler)


def fake_loader(value='foo'):
    return {'test': {'path': value}}


class ServiceClientFactoryTests(TestCase):

    def setUp(self):
        self.loader = LoaderNamespace()
        self.loader.register_namespace('logging', 'logging')
        self.loader.register_namespace('sc', 'service_client')
        self.loader.register_namespace('sc-plugins', 'service_client.plugins')
        self.loader.register_namespace('here', __name__)
        register_logging_factories(self.loader)
        register_service_client_factories(self.loader)

    def test_service_client_basic(self):

        definition = {'name': 'test1',
                      'spec': {'test': {'path': 'baz'}},
                      'parser': 'sc:json.json_decoder',
                      'serializer': 'sc:json.json_encoder',
                      'logger': {'type': 'logging:Logger',
                                 'params': {'name': 'foo.bar.test.2',
                                            'handlers': ['logging:NullHandler']}}}

        sc = self.loader.factory('sc:ServiceClient', **definition)

        self.assertIsInstance(sc, ServiceClient)
        self.assertEqual(sc.name, 'test1')
        self.assertEqual(sc.spec, definition['spec'])
        self.assertEqual(sc.parser, json_decoder)
        self.assertEqual(sc.serializer, json_encoder)
        self.assertEqual(sc.logger, getLogger('foo.bar.test.2'))
        self.assertEqual(len(sc.logger.handlers), 1)
        self.assertIsInstance(sc.logger.handlers[0], NullHandler)

    def test_service_client_with_plugins(self):
        definition = {'name': 'test1',
                      'spec': {'test': {'path': 'baz'}},
                      'plugins': ['sc-plugins:PathTokens',
                                  {'type': 'sc-plugins:InnerLogger',
                                   'params': {'logger': {'type': 'logging:Logger',
                                                         'params': {'name': 'foo.bar.test.3',
                                                                    'handlers': ['logging:NullHandler']}}}}]}

        sc = self.loader.factory('sc:ServiceClient', **definition)

        self.assertIsInstance(sc, ServiceClient)
        self.assertEqual(sc.name, 'test1')
        self.assertEqual(sc.spec, definition['spec'])
        self.assertEqual(len(sc._plugins), 2)
        self.assertIsInstance(sc._plugins[0], PathTokens)
        self.assertIsInstance(sc._plugins[1], InnerLogger)
        self.assertEqual(sc._plugins[1].logger, getLogger('foo.bar.test.3'))
        self.assertEqual(len(sc._plugins[1].logger.handlers), 1)
        self.assertIsInstance(sc._plugins[1].logger.handlers[0], NullHandler)

    def test_service_client_with_spec_loader(self):
        definition = {'name': 'test1',
                      'spec_loader': {'type': 'here:fake_loader',
                                      'params': {'value': 'baz'}}}

        sc = self.loader.factory('sc:ServiceClient', **definition)

        self.assertIsInstance(sc, ServiceClient)
        self.assertEqual(sc.name, 'test1')
        self.assertEqual(sc.spec, {'test': {'path': 'baz'}})
