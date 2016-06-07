import os
from unittest.case import TestCase
from service_client.spec_loaders import json_loader, yaml_loader, configuration_loader

SPECS_DIR = os.path.join(os.path.dirname(__file__), 'specs')


class JsonLoaderTests(TestCase):

    def test_load_spec(self):
        spec = json_loader(os.path.join(SPECS_DIR, 'spec.json'))
        self.assertEqual(spec, {"endpoint1": {"path": "/ssssss",
                                              "method": "get"}})


class YamlLoaderTests(TestCase):

    def test_load_spec(self):
        spec = yaml_loader(os.path.join(SPECS_DIR, 'spec.yaml'))
        self.assertEqual(spec, {"endpoint1": {"path": "/ssssss",
                                              "method": "get"}})


class ConfigurationLoaderTests(TestCase):

    def test_load_spec(self):
        spec = configuration_loader(os.path.join(SPECS_DIR, 'spec_extends.yaml'))
        self.assertEqual(spec, {"endpoint1": {"path": "/ssssss",
                                              "method": "get"},
                                "endpoint2": {"path": "/bbbbbb",
                                              "method": "post"}})
