import weakref
from asyncio import coroutine
from urllib.parse import quote_plus
from aiohttp.multidict import CIMultiDict
from aiohttp.multipart import MultipartWriter

from service_client.utils import IncompleteFormatter
from dirty_loader import LoaderNamespaceReversedCached


class BasePlugin:

    def assign_service_client(self, service_client):
        self.service_client = service_client

    @property
    def service_client(self):
        return self._service_client()

    @service_client.setter
    def service_client(self, service_client):
        self._service_client = weakref.ref(service_client)


class Path(BasePlugin):

    def __init__(self, default_substitutions=None):
        self.default_substitutions = default_substitutions or {}

    @coroutine
    def prepare_path(self, service_desc, session, request_params, path):
        substitutions = self.default_substitutions.copy()
        substitutions.update(request_params)
        formatter = IncompleteFormatter()
        ret = formatter.format(path, **{k: quote_plus(str(v)) for k, v in substitutions.items()})
        for field in formatter.get_substituted_fields():
            try:
                request_params.pop(field)
            except KeyError:
                pass
        return ret


class Headers(BasePlugin):

    def __init__(self, default_headers={}):
        self.default_headers = default_headers.copy()

    @coroutine
    def prepare_request_params(self, service_desc, session, request_params):
        headers = request_params.get('headers', CIMultiDict()).copy()
        if not isinstance(headers, CIMultiDict):
            headers = CIMultiDict(headers)
        headers.update(self.default_headers)
        headers.update(service_desc.get('headers', {}))
        headers.update(request_params.get('headers', {}))
        request_params['headers'] = headers


class Timeout(BasePlugin):

    def __init__(self, default_timeout=None):
        self.default_timeout = default_timeout

    @coroutine
    def prepare_request_params(self, service_desc, session, request_params):
        request_params['timeout'] = request_params.get('timeout',
                                                       service_desc.get('timeout',
                                                                        self.default_timeout))
        if request_params['timeout']:
            request_params['timeout'] = int(request_params['timeout'])


class QueryParams(BasePlugin):

    @coroutine
    def prepare_request_params(self, service_desc, session, request_params):
        query_params = service_desc.get('query_params', {}).copy()
        query_params.update(request_params.get('params', {}))
        request_params['params'] = query_params


class Mock(BasePlugin):

    def __init__(self, namespaces=None):

        self.loader = LoaderNamespaceReversedCached()

        if namespaces:
            for n, m in namespaces.items():
                self.loader.register_namespace(n, m)

    def _create_mock(self, mock_desc, loop):
        """
        The class imported should have the __call__ function defined to be an object directly callable
        """
        return self.loader.factory(mock_desc.get('mock_type'), mock_desc, loop=loop)

    @coroutine
    def prepare_session(self, service_desc, session, request_params):
        mock_desc = service_desc.get('mock', {})
        session.set_attr_wrap('request', self._create_mock(mock_desc, loop=self.service_client.loop))

        try:
            session.request.set_request_params(request_params)
        except AttributeError:
            pass


class Multipart(BasePlugin):

    def __init__(self, default_multipart_content_type='form-data',
                 default_content_disposition='attachment'):
        self.default_multipart_content_type = default_multipart_content_type
        self.default_content_disposition = default_content_disposition

    @coroutine
    def before_request(self, service_desc, session, request_params):
        if request_params['method'].upper() in ['GET', 'DELETE'] or 'files' not in request_params:
            return

        try:
            multipart_content_type = service_desc['multipart']['content-type']
        except KeyError:  # pragma: no cover
            multipart_content_type = self.default_multipart_content_type

        try:
            content_type = request_params['headers'].pop('content-type')
        except KeyError:  # pragma: no cover
            content_type = ''

        mp = MultipartWriter(multipart_content_type)

        try:
            data = request_params['data']
            mp.append(data, {'content-type': content_type})
        except KeyError:  # pragma: no cover
            pass

        files = request_params.pop('files')

        for f in files:
            try:
                file_headers = f['headers']
            except KeyError:
                file_headers = None
            part = mp.append(f['file'], file_headers)

            try:
                content_disposition = f['content-disposition']
            except KeyError:
                try:
                    content_disposition = service_desc['multipart']['content-disposition']
                except KeyError:  # pragma: no cover
                    content_disposition = self.default_content_disposition

            params = {}
            try:
                params['filename'] = f['filename']
            except KeyError:
                pass

            part.set_content_disposition(content_disposition, **params)

        request_params['data'] = mp
