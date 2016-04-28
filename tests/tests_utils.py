from unittest.case import TestCase

from service_client.utils import IncompleteFormatter


class TestIncompleteFormatter(TestCase):

    def setUp(self):

        self.formatter = IncompleteFormatter()

    def test_all_items_kwargs(self):

        self.assertEqual(self.formatter.format("Test {var1} with {var2} kwarg", var1="first", var2=2),
                         "Test first with 2 kwarg")

        self.assertEqual(self.formatter.get_substituted_fields(), ['var1', 'var2'])
        self.assertEqual(self.formatter.get_not_substituted_fields(), [])

    def test_one_items_kwargs(self):
        self.assertEqual(self.formatter.format("Test {var1} with {var2} kwarg", var1="first"),
                         "Test first with {var2} kwarg")

        self.assertEqual(self.formatter.get_substituted_fields(), ['var1'])
        self.assertEqual(self.formatter.get_not_substituted_fields(), ['var2'])

    def test_no_items_kwargs(self):
        self.assertEqual(self.formatter.format("Test {var1} with {var2} kwarg"),
                         "Test {var1} with {var2} kwarg")

        self.assertEqual(self.formatter.get_substituted_fields(), [])
        self.assertEqual(self.formatter.get_not_substituted_fields(), ['var1', 'var2'])

    def test_all_items_indexed_args(self):
        self.assertEqual(self.formatter.format("Test {0} with {1} indexed args", "first", 2),
                         "Test first with 2 indexed args")

        self.assertEqual(self.formatter.get_substituted_fields(), ['0', '1'])
        self.assertEqual(self.formatter.get_not_substituted_fields(), [])

    def test_one_items_indexed_args(self):
        self.assertEqual(self.formatter.format("Test {0} with {1} indexed args", 'first'),
                         "Test first with {1} indexed args")

        self.assertEqual(self.formatter.get_substituted_fields(), ['0'])
        self.assertEqual(self.formatter.get_not_substituted_fields(), ['1'])

    def test_no_items_indexed_args(self):
        self.assertEqual(self.formatter.format("Test {0} with {1} indexed args"),
                         "Test {0} with {1} indexed args")

        self.assertEqual(self.formatter.get_substituted_fields(), [])
        self.assertEqual(self.formatter.get_not_substituted_fields(), ['0', '1'])

    def test_all_items_not_indexed_args(self):
        self.assertEqual(self.formatter.format("Test {} with {} indexed args", "first", 2),
                         "Test first with 2 indexed args")

        self.assertEqual(self.formatter.get_substituted_fields(), ['0', '1'])
        self.assertEqual(self.formatter.get_not_substituted_fields(), [])

    def test_one_items_not_indexed_args(self):
        self.assertEqual(self.formatter.format("Test {} with {} indexed args", 'first'),
                         "Test first with {1} indexed args")

        self.assertEqual(self.formatter.get_substituted_fields(), ['0'])
        self.assertEqual(self.formatter.get_not_substituted_fields(), ['1'])

    def test_no_items_not_indexed_args(self):
        self.assertEqual(self.formatter.format("Test {} with {} indexed args"),
                         "Test {0} with {1} indexed args")

        self.assertEqual(self.formatter.get_substituted_fields(), [])
        self.assertEqual(self.formatter.get_not_substituted_fields(), ['0', '1'])