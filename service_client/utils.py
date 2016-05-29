import string
from string import Formatter

import random


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
