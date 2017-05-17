from textwrap import dedent
from typing import Optional, Union
from unittest.case import TestCase

from service_client.utils import IncompleteFormatter, random_token, build_parameter_object


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


class RandomTokenTest(TestCase):

    def test_random_token(self):
        self.assertNotEqual(random_token(), random_token())
        self.assertNotEqual(random_token(), random_token())
        self.assertNotEqual(random_token(), random_token())

    def test_default_length(self):
        self.assertEqual(len(random_token()), 10)

    def test_custom_length(self):
        self.assertEqual(len(random_token(20)), 20)


class FakeModel:

    def __init__(self, data=None):
        try:
            self.fieldname_1 = data['fieldname_1']
        except (KeyError, TypeError):
            self.fieldname_1 = None


class BuildParameterObjectTests(TestCase):

    class Fake:

        @build_parameter_object
        def method_union(self, request: Union[FakeModel, None]):
            return request

        @build_parameter_object(arg_name='request_1', arg_index=1, arg_class=FakeModel)
        def method_no_anno_extra_params(self, param_1, request_1, param_2):
            """
            :param param_1:
            :param request_1:
            :param param_2:
            :return:
            """
            return param_1, request_1, param_2

        @build_parameter_object
        def method_optional(self, request: Optional[FakeModel]):
            return request

        @build_parameter_object
        def method_class(self, request: FakeModel):
            return request

    def setUp(self):
        self.object = self.Fake()

    def test_using_union_positional(self):
        request = FakeModel()
        self.assertEqual(self.object.method_union(request), request)

    def test_using_union_keyword(self):
        request = FakeModel()
        self.assertEqual(self.object.method_union(request=request), request)

    def test_using_union_build(self):
        result = self.object.method_union(fieldname_1=1)
        self.assertIsInstance(result, FakeModel)
        self.assertEqual(result.fieldname_1, 1)

    def test_using_union_build_empty(self):
        result = self.object.method_union()
        self.assertIsInstance(result, FakeModel)
        self.assertIsNone(result.fieldname_1)

    def test_using_optional_positional(self):
        request = FakeModel()
        self.assertEqual(self.object.method_optional(request), request)

    def test_using_optional_keyword(self):
        request = FakeModel()
        self.assertEqual(self.object.method_optional(request=request), request)

    def test_using_optional_build(self):
        result = self.object.method_optional(fieldname_1=1)
        self.assertIsInstance(result, FakeModel)
        self.assertEqual(result.fieldname_1, 1)

    def test_using_optional_build_empty(self):
        result = self.object.method_optional()
        self.assertIsInstance(result, FakeModel)
        self.assertIsNone(result.fieldname_1)

    def test_using_class_positional(self):
        request = FakeModel()
        self.assertEqual(self.object.method_class(request), request)

    def test_using_class_keyword(self):
        request = FakeModel()
        self.assertEqual(self.object.method_class(request=request), request)

    def test_using_class_build(self):
        result = self.object.method_class(fieldname_1=1)
        self.assertIsInstance(result, FakeModel)
        self.assertEqual(result.fieldname_1, 1)

    def test_using_class_build_empty(self):
        result = self.object.method_class()
        self.assertIsInstance(result, FakeModel)
        self.assertIsNone(result.fieldname_1)

    def test_using_no_anno_extra_params_positional(self):
        request = FakeModel()
        self.assertEqual(self.object.method_no_anno_extra_params(1, request, 2), (1, request, 2))

    def test_using_no_anno_extra_params_keyword(self):
        request = FakeModel()
        self.assertEqual(self.object.method_no_anno_extra_params(param_1=1, request_1=request, param_2=2),
                         (1, request, 2))

    def test_using_no_anno_extra_params_build(self):
        result = self.object.method_no_anno_extra_params(1, fieldname_1=1, param_2=2)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[2], 2)
        self.assertIsInstance(result[1], FakeModel)
        self.assertEqual(result[1].fieldname_1, 1)

    def test_using_no_anno_extra_params_build_empty(self):
        result = self.object.method_no_anno_extra_params(1, param_2=2)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[2], 2)
        self.assertIsInstance(result[1], FakeModel)
        self.assertIsNone(result[1].fieldname_1)

    def test_doc(self):
        self.assertEqual(self.object.method_no_anno_extra_params.__doc__,
                         dedent("""
                                :param param_1:
                                :param request_1:
                                :param param_2:
                                :return:

                                It is possible to use keyword parameters to build an
                                object :class:`~tests.tests_utils.FakeModel` for parameter ``request_1``."""),
                         self.object.method_no_anno_extra_params.__doc__)
