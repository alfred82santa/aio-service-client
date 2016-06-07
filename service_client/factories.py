from logging import Logger
from dirty_loader.factories import BaseFactory, instance_params
from . import ServiceClient
from .plugins import BasePlugin, BaseLogger


class ServiceClientFactory(BaseFactory):

    def __call__(self, spec=None, spec_loader=None, plugins=None,
                 parser=None, serializer=None, logger=None, **kwargs):
        if spec_loader:
            loader_class, params = instance_params(spec_loader)
            loader = self.loader.load_class(loader_class)
            spec = loader(**params)

        try:
            loaded_plugins = []
            for plugin in plugins:
                if not isinstance(plugin, BasePlugin):
                    klass, params = instance_params(plugin)
                    plugin = self.loader.factory(klass, **params)
                loaded_plugins.append(plugin)
            plugins = loaded_plugins
        except TypeError:
            pass

        if isinstance(parser, str):
            parser = self.loader.load_class(parser)

        if isinstance(serializer, str):
            serializer = self.loader.load_class(serializer)

        if logger and not isinstance(logger, Logger):
            klass, params = instance_params(logger)
            logger = self.loader.factory(klass, **params)

        return super(ServiceClientFactory, self).__call__(spec=spec, plugins=plugins, parser=parser,
                                                          serializer=serializer, logger=logger, **kwargs)


class LoggerPluginFactory(BaseFactory):

    def __call__(self, logger, **kwargs):
        if logger and not isinstance(logger, Logger):
            klass, params = instance_params(logger)
            logger = self.loader.factory(klass, **params)

        return super(LoggerPluginFactory, self).__call__(logger=logger, **kwargs)


def register_service_client_factories(loader):
    loader.register_factory(ServiceClient, ServiceClientFactory)
    loader.register_factory(BaseLogger, LoggerPluginFactory)
