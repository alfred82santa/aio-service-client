from string import Formatter


class IncompleteFormatter(Formatter):

    """
    String formatter to safe replace every placeholder. When the placeholder is not
    replaced it remains the same in the string
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
