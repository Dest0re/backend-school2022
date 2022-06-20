import logging
from typing import Mapping
from http import HTTPStatus

from aiohttp.web_exceptions import (
    HTTPException, HTTPBadRequest, HTTPInternalServerError, HTTPMethodNotAllowed,
    HTTPRedirection
)
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.payload import JsonPayload
from marshmallow import ValidationError


log = logging.getLogger(__name__)


def format_http_error(http_error_cls, message: str | None = None,
                      fields: Mapping | None = None) -> HTTPException:
    status = HTTPStatus(http_error_cls.status_code)
    error = {
        'code': status.name.lower(),
        'message': message or status.description
    }

    if fields:
        error['fields'] = fields

    return http_error_cls(body=error)


def handle_validation_error(error: ValidationError, *_):
    raise format_http_error(HTTPBadRequest, 'Request validation has failed',
                            error.messages)


@middleware
async def error_middleware(request: Request, handler):
    try:
        return await handler(request)

    except HTTPMethodNotAllowed as exc:
        raise exc

    except HTTPRedirection as exc:
        raise exc

    except HTTPException as exc:
        if not isinstance(exc.body, JsonPayload):
            exc = format_http_error(exc.__class__, exc.body)
        raise exc

    except ValidationError as exc:
        raise handle_validation_error(exc)

    except Exception:
        log.exception('Unhandled Exception')
        raise format_http_error(HTTPInternalServerError)
