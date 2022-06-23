import logging
from collections.abc import AsyncIterable
from functools import partial
from typing import Mapping
from types import MappingProxyType, AsyncGeneratorType

from configargparse import Namespace
from aiohttp import PAYLOAD_REGISTRY
from aiohttp.web import Application
from aiohttp_apispec import validation_middleware, setup_aiohttp_apispec
from aiohttp_swagger import setup_swagger

from megamarket.utils.pg import setup_pg
from megamarket.api.handlers import HANDLERS
from megamarket.api.middleware import error_middleware, handle_validation_error
from megamarket.api.payloads import JsonPayload, AsyncStreamJsonPayload

MEGABYTE = 1024 ** 1024
MAX_REQUEST_SIZE = 5 * MEGABYTE


log = logging.getLogger(__name__)


async def swagger(app):
    setup_swagger(
        app=app, swagger_url='/doc', swagger_info=app['swagger_dict']
    )


def create_app(args: Namespace) -> Application:
    app = Application(
        client_max_size=MAX_REQUEST_SIZE,
        middlewares=[error_middleware, validation_middleware]
    )

    app.cleanup_ctx.append(partial(setup_pg, args=args))

    for handler in HANDLERS:
        log.debug('Registering handler: %r as %r', handler, handler.URL_PATH)
        app.router.add_route('*', handler.URL_PATH, handler)

    setup_aiohttp_apispec(app=app, title='Megamarket API',
                          error_callback=handle_validation_error)

    app.on_startup.append(swagger)

    PAYLOAD_REGISTRY.register(JsonPayload, (Mapping, MappingProxyType))
    PAYLOAD_REGISTRY.register(AsyncStreamJsonPayload, (AsyncGeneratorType, AsyncIterable))

    return app
