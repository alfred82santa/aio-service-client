import json


def json_encoder(content, *args, **kwargs):
    """
    Json encoder to be used by service_client. For the moment is just a proxy to json.dumps
    """
    return json.dumps(content)


def json_decoder(content, *args, **kwargs):
    """
    Json decoder parser to be used by service_client
    """
    if not content:
        return None
    json_value = content.decode()
    return json.loads(json_value)
