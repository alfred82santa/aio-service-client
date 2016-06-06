

def json_loader(filename):
    from json import load
    with open(filename) as f:
        return load(f)


def yaml_loader(filename):
    from yaml import load
    with open(filename) as f:
        return load(f)


def configuration_loader(filename):
    from collections import Mapping
    from configure import Configuration
    config = Configuration.from_file(filename)
    config.configure()

    def to_dict(mapping):
        return {k: (to_dict(v) if isinstance(v, Mapping) else v) for k, v in mapping.items()}

    return to_dict(config)
