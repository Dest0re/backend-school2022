import datetime
import typing
from functools import singledispatch, partial
import json

import aiohttp
from asyncpg import Record
from aiohttp.payload import PAYLOAD_REGISTRY, JsonPayload as BaseJsonPayload, Payload
from aiohttp.typedefs import JSONEncoder

from megamarket.api.schema import DATETIME_FORMAT, ShopUnitType


__all__ = (
    'JsonPayload'
)


@singledispatch
def convert(value):
    raise TypeError(f'Unserializable value: {value!r}')


@convert.register(Record)
def convert_asyncpg_record(value: Record):
    return dict(value)


@convert.register(bytes)
def convert_bytes(value: bytes):
    return value.decode()


@convert.register(datetime.datetime)
def convert_datetime(value: datetime.datetime):
    return value.strftime(DATETIME_FORMAT)


@convert.register(ShopUnitType)
def convert_shop_unit_type(value: ShopUnitType):
    return value.value


dumps = partial(json.dumps, default=convert, ensure_ascii=False)


class JsonPayload(BaseJsonPayload):
    def __init__(self,
                 value: typing.Any,
                 encoding: str = 'utf-8',
                 content_type: str = 'application/json',
                 dumps: JSONEncoder = dumps,
                 *args: typing.Any,
                 **kwargs: typing.Any
                 ):
        super().__init__(
            value, encoding, content_type, dumps, *args, **kwargs
        )


class AsyncStreamJsonPayload(Payload):
    def __init__(self, value, encoding='utf-8',
                 content_type='application/json',
                 root_object: str = None,
                 *args, **kwargs):
        super().__init__(value, content_type=content_type, encoding=encoding, *args, **kwargs)
        self.root_object = root_object

    async def write(self, writer):
        if self.root_object is not None:
            await writer.write(('{%s: ' % self.root_object).encode(self.encoding))

        async for row in self._value:
            await writer.write(row.encode(self.encoding))

        if self.root_object is not None:
            await writer.write(b'}')
