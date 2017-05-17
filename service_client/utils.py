import string
from inspect import signature
from string import Formatter
from textwrap import dedent

import random
from functools import wraps


class IncompleteFormatter(Formatter):
    """
    String formatter to safe replace every placeholder. When the placeholder is not
    replaced it remains the same in the string.
    """

    def __init__(self):
        self._substituted_fields = []
        self._not_substituted_fields = []

    def _manage_substituted_field(self, field_name, args, kwargs):
        self._substituted_fields.append(field_name)

    def _manage_not_substituted_field(self, field_name, args, kwargs):
        self._not_substituted_fields.append(field_name)

    def get_field(self, field_name, args, kwargs):
        try:
            val = super(IncompleteFormatter, self).get_field(field_name, args, kwargs)
        except (KeyError, IndexError):
            self._manage_not_substituted_field(field_name, args, kwargs)
            val = '{{{0}}}'.format(field_name), field_name
        else:
            self._manage_substituted_field(field_name, args, kwargs)
        return val

    def get_substituted_fields(self):
        return self._substituted_fields

    def get_not_substituted_fields(self):
        return self._not_substituted_fields


def random_token(length=10):
    """
    Builds a random string.

    :param length: Token length. **Default:** 10
    :type length: int
    :return: str
    """
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                   for _ in range(length))


class ObjectWrapper:

    def __init__(self, obj):
        self.__dict__['_obj'] = None
        self.__dict__['_data'] = {}
        self.set_warpped_object(obj)

    def __getattr__(self, item):
        try:
            return self._data[item]
        except KeyError:
            return getattr(self._obj, item)

    def __setattr__(self, key, value):
        if hasattr(self._obj, key):  # pragma: no cover
            return setattr(self._obj, key, value)
        else:
            self._data[key] = value

    def __str__(self):  # pragma: no cover
        return str(self._obj)

    def __repr__(self):  # pragma: no cover
        return repr(self._obj)

    def __eq__(self, other):  # pragma: no cover
        return self._obj.__eq__(other)

    def override_attr(self, key, value):
        self.__dict__[key] = value

    def decorate_attr(self, key, decorator):
        attr = getattr(self, key)
        self.__dict__[key] = decorator(attr)

    def set_warpped_object(self, obj):
        self.__dict__['_obj'] = obj

    def get_wrapper_data(self):
        return {k: v for k, v in self._data.items() if not callable(v)}


def build_parameter_object(func=None, *, arg_name='request',
                           arg_index=0, arg_class=None, init_arg_name='data'):
    def inner(func):
        klass = arg_class
        type_hints = signature(func).parameters
        if klass is None:
            klass = type_hints[arg_name].annotation

            try:
                klass = klass.__args__[0]
            except (AttributeError, IndexError):  # pragma: no cover
                try:
                    klass = klass.__union_params__[0]
                except (AttributeError, IndexError):
                    pass

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            use_index = False
            try:
                args = list(args)
                obj = args.pop(arg_index)
                use_index = True
            except IndexError:
                try:
                    obj = kwargs[arg_name]
                except KeyError:
                    obj = klass(**{init_arg_name: kwargs})

            new_kwargs = {}
            if use_index:
                args.insert(arg_index, obj)
            else:
                new_kwargs[arg_name] = obj

            new_kwargs.update({k: v for k, v in kwargs.items()
                               if k in type_hints and k != arg_name})
            return func(self, *args, **new_kwargs)

        wrapper.__doc__ = dedent(func.__doc__ or '') + dedent("""
            It is possible to use keyword parameters to build an
            object :class:`~{0}` for parameter ``{1}``.""").format('.'.join([klass.__module__,
                                                                             klass.__name__]),
                                                                   arg_name)

        return wrapper

    if func:
        return inner(func)
    return inner
