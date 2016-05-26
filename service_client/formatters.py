from urllib.parse import urlencode
from http.server import BaseHTTPRequestHandler
from logging import Formatter, PercentStyle, StrFormatStyle, StringTemplateStyle

_STYLES = {
    '%': PercentStyle,
    '{': StrFormatStyle,
    '$': StringTemplateStyle,
}


class _FakeRecord:

    def __init__(self, data):
        self.__dict__.update(data)


class ServiceClientFormatter(Formatter):

    def __init__(self, fmt=None, request_fmt='', response_fmt='',
                 exception_fmt='', parse_exception_fmt='',
                 headers_fmt='', headers_sep='',
                 datefmt=None, style='%'):

        super(ServiceClientFormatter, self).__init__(fmt=fmt, datefmt=datefmt, style=style)

        self._request_style = _STYLES[style](request_fmt)
        self._response_style = _STYLES[style](response_fmt)
        self._exception_style = _STYLES[style](exception_fmt)
        self._parse_exception_style = _STYLES[style](parse_exception_fmt)
        self._headers_style = _STYLES[style](headers_fmt)
        self._headers_sep = headers_sep

    def format_request_message(self, record):
        return self._request_style.format(record)

    def format_response_message(self, record):
        return self._response_style.format(record)

    def format_exception_message(self, record):
        return self._exception_style.format(record)

    def format_parse_exception_message(self, record):
        return self._parse_exception_style.format(record)

    def formatMessage(self, record):
        try:
            record.headers = self._headers_sep.join([self._headers_style.format(_FakeRecord({'name': k, 'value': v}))
                                                     for k, v in record.headers.items()])
        except AttributeError:
            pass

        try:
            record.elapsed = "{} ms".format(int(record.elapsed.total_seconds() * 1000))
        except AttributeError:
            pass

        try:
            record.status_text = BaseHTTPRequestHandler.responses[record.status_code][0]
        except KeyError:
            record.status_text = 'Unknown'
        except AttributeError:
            pass

        record.full_url = record.url
        try:
            record.query_params = urlencode(record.params)
            record.full_url = "?".join([record.full_url, record.query_params])
        except AttributeError:
            pass

        try:
            record.exception_repr = repr(record.exception)
        except AttributeError:
            pass

        s = super(ServiceClientFormatter, self).formatMessage(record)

        if record.action == 'REQUEST':
            return s + self.format_request_message(record)
        elif record.action == 'RESPONSE':
            return s + self.format_response_message(record)
        elif record.action == 'EXCEPTION':
            if hasattr(record, 'body'):
                return s + self.format_parse_exception_message(record)
            else:
                return s + self.format_exception_message(record)
        else:
            return s
