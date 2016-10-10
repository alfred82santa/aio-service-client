from logging import Logger

from dirty_loader.factories import BaseFactory, instance_params

from . import ServiceClient
from .plugins import BasePlugin, BaseLogger


def load_spec_by_sepc_loader(spec_loader, loader):
    loader_class, params = instance_params(spec_loader)
    loader = loader.load_class(loader_class)
    return loader(**params)


class ServiceClientFactory(BaseFactory):

    def __call__(self, spec=None, spec_loader=None, plugins=None,
                 parser=None, serializer=None, logger=None, **kwargs):
        if spec_loader:
            spec = load_spec_by_sepc_loader(spec_loader, self.loader)

        try:
            plugins = self.iter_loaded_item_list(plugins, BasePlugin)
        except TypeError:  # pragma: no cover
            pass

        if isinstance(parser, str):
            parser = self.loader.load_class(parser)

        if isinstance(serializer, str):
            serializer = self.loader.load_class(serializer)

        try:
            logger = self.load_item(logger, Logger)
        except TypeError:  # pragma: no cover
            pass

        return super(ServiceClientFactory, self).__call__(spec=spec, plugins=plugins, parser=parser,
                                                          serializer=serializer, logger=logger, **kwargs)


class LoggerPluginFactory(BaseFactory):

    def __call__(self, logger, **kwargs):
        try:
            logger = self.load_item(logger, Logger)
        except TypeError:  # pragma: no cover
            pass

        return super(LoggerPluginFactory, self).__call__(logger=logger, **kwargs)


def register_service_client_factories(loader):
    loader.register_factory(ServiceClient, ServiceClientFactory)
    loader.register_factory(BaseLogger, LoggerPluginFactory)
