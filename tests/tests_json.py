from unittest.case import TestCase

from service_client.json import json_encoder, json_decoder


class TestJsonParser(TestCase):

    def setUp(self):
        self.parser = json_decoder

    def test_parse(self):

        self.assertEqual(self.parser(b'{"pepito":"grillo"}'),
                         {"pepito": "grillo"})

    def test_parse_none(self):
        self.assertIsNone(self.parser(None))

class TestJsonSerializer(TestCase):

    def setUp(self):
        self.serializer = json_encoder

    def test_serialize_data(self):

        self.assertEqual('{"pepito": "grillo"}',
                         self.serializer({"pepito": "grillo"}))


