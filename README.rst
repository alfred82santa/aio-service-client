|travis-master| |coverall-master| |doc-master| |pypi-downloads| |pypi-lastrelease| |python-versions|
|project-status| |project-license| |project-format| |project-implementation|

.. |travis-master| image:: https://travis-ci.org/alfred82santa/aio-service-client.svg?branch=master
    :target: https://travis-ci.org/alfred82santa/aio-service-client

.. |coverall-master| image:: https://coveralls.io/repos/alfred82santa/aio-service-client/badge.svg?branch=master&service=github
    :target: https://coveralls.io/r/alfred82santa/aio-service-client?branch=master

.. |doc-master| image:: https://readthedocs.org/projects/aio-service-client/badge/?version=latest
    :target: http://aio-service-client.readthedocs.io/?badge=latest
    :alt: Documentation Status

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/aio-service-client.svg
    :target: https://pypi.python.org/pypi/aio-service-client/
    :alt: Downloads

.. |pypi-lastrelease| image:: https://img.shields.io/pypi/v/aio-service-client.svg
    :target: https://pypi.python.org/pypi/aio-service-client/
    :alt: Latest Version

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/aio-service-client.svg
    :target: https://pypi.python.org/pypi/aio-service-client/
    :alt: Supported Python versions

.. |project-status| image:: https://img.shields.io/pypi/status/aio-service-client.svg
    :target: https://pypi.python.org/pypi/aio-service-client/
    :alt: Development Status

.. |project-license| image:: https://img.shields.io/pypi/l/aio-service-client.svg
    :target: https://pypi.python.org/pypi/aio-service-client/
    :alt: License

.. |project-format| image:: https://img.shields.io/pypi/format/aio-service-client.svg
    :target: https://pypi.python.org/pypi/aio-service-client/
    :alt: Download format

.. |project-implementation| image:: https://img.shields.io/pypi/implementation/aio-service-client.svg
    :target: https://pypi.python.org/pypi/aio-service-client/
    :alt: Supported Python implementations


========================
Service Client Framework
========================

Service Client Framework powered by Python asyncio.

The easiest way to implement a client to work with a service REST API.

Features
========

- Easy way to make request to service.
- AsyncIO implementation using aiohttp.
- Powerful plugin system.
- Useful plugins.
- Mock plugin in order to make tests.
- Opensource license: GNU LGPLv3

Installation
============

.. code-block:: bash

    $ pip install aio-service-client

Getting started
===============

Service client framework is used to call HTTP service API's. So, you must define how to
communicate with this service API defining its endpoint:

.. code-block:: python

    spec = {"get_users": {"path": "/user",
                          "method": "get"},
            "get_user_detail": {"path": "/user/{user_id}",
                                "method": "get"},
            "create_user": {"path": "/user",
                            "method": "post"},
            "update_user": {"path": "/user/{user_id}",
                            "method": "put"}}

Imagine you are using a Rest JSON API in order to manage users. So, you data must be sent
as a JSON and response must be a JSON string. It mean you must serialize every request payload
to a JSON, and parse every response as JSON. So, you only need to define JSON parser and serializer
for your service:

.. code-block:: python

    service = ServiceClient(spec=spec,
                            plugins=[PathToken()],
                            base_path="http://example.com",
                            parser=json_decoder,
                            serializer=json_encoder)

So, you are ready to make request to service API:

.. code-block:: python

    resp = yield from service.call("get_users")
    # it could be called directly
    # resp = yield from service.get_users()

    # if response is like:
    # {"users": {"item": [{"userId": "12", "username": "foo"}, {"userId": "13", "username": "bar"}], "count": 2}
    print("Count: %d" % resp.data['users']['count'])
    for user in resp.data['users']['items']:
        print("User `%s`: %s" % (user['userId'], user['username']))

In order to send a payload you must use ``payload`` keyword on call:

.. code-block:: python

    resp = yield from service.call("create_user", payload={"username": "foobar"})
    # it could be called directly
    # resp = yield from service.create_user(payload={"username": "foobar"})

    # it will make a request like:
    # POST http://example.com/user
    #
    # {"username": "foobar"}


Changelog
=========

v0.5.2
------

- Made compatible with aiohttp 1.0.x.
- Simplified factory code.

v0.5.1
------

- Resolved problem with requests streamed.

v0.5.0
------

- Added factories
- Added spec loaders

v0.4.1
------

- Fix elapsed data on logs.

v0.4.0
------

- Added new ``Pool`` plugin.
- Improved ``Elapsed`` plugin.
- Added new hook in order to allow plugins to override response methods.

v0.3.1
------

- Fix response when using Timeout plugin.

v0.3.0
------

- Added TrackingToken plugin. Token is added to session and to response.
- Added a log formatter.
- Removed tracking token stuff from log plugins.
- Improved log plugins. They avoid to print body if it is streamed or must be hidden.
- Improved session wrapper.

Plugins
=======

PathTokens
----------

It allows to fill placeholders on path in order to build uri.

.. code-block:: python

    service = ServiceClient(spec={"endpoint1": {"method": "get",
                                                "path": "/endpoint/{placeholder1}/{placeholder2}"}},
                            plugins=[PathToken()],
                            base_path="http://example.com")

    resp = yield from service.call("endpoint1", placeholder1=21, placeholder1="foo")
    # It will make request:
    # GET http://example.com/endpoint/21/foo


Headers
-------

It allows to define default headers, endpoint headers and request headers.


.. code-block:: python

    service = ServiceClient(spec={"endpoint1": {"method": "get",
                                                "path": "/endpoint/{placeholder1}/{placeholder2}",
                                                "headers": {"X-fake-header": "header; data"}}},
                            plugins=[Headers(headers={"content-type": "application/json"})],
                            base_path="http://example.com")

    resp = yield from service.call("endpoint1", headers={"X-other-fake-header": "foo"})
    # It will make request:
    # GET http://example.com/endpoint/21/foo
    # X-fake-header: header; data
    # content-type: application/json
    # X-other-fake-header: foo

Timeout
-------

It allows to define default timeout for service request, endpoint or request.

Elapsed
-------

It adds elapsed time to response.

TrackingToken
-------------

It allows to assign a token for each pair request/response in order to identify them.

QueryParams
-----------

It allows to use query parameters on request. They could be defined at service client, endpoint or request.

InnerLogger
-----------

It allows to log request after serialize and response before parse.

OuterLogger
-----------

It allows to log request before serialize and response after parse.
