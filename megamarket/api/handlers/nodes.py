import asyncio
import time
from collections.abc import AsyncIterable
from datetime import datetime

from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp_apispec.decorators import response_schema
from sqlalchemy.ext.asyncio import AsyncEngine

from .base import BaseView
from megamarket.api.schema import ShopUnitSchema
from ...utils.streamers import ShopUnitStreamer, shop_unit_streamer_from_record, do_stream


class GetShopUnitQuery(AsyncIterable):
    def __init__(self, parent_unit_id: str,
                 pg: AsyncEngine,
                 timeout: int = None,
                 from_date: datetime | None = None,
                 to_date: datetime | None = datetime.now()):
        self._parent_unit_id = parent_unit_id
        self._pg = pg
        self._timeout = timeout
        self._from_date = from_date
        self._to_date = to_date

    async def __aiter__(self):
        async with self._pg.begin() as conn:
            unit = await ShopUnitStreamer.get_unit_record_by_id(self._parent_unit_id, conn,
                                                                self._from_date, self._to_date)

            if not unit:
                raise KeyError

            unit = shop_unit_streamer_from_record(unit, conn,
                                                  self._from_date, self._to_date)

            exec_time = time.time()
            async for chunk in do_stream(unit):
                if self._timeout and time.time() - exec_time > self._timeout:
                    raise asyncio.TimeoutError()

                yield chunk


class NodesView(BaseView):
    URL_PATH = r'/nodes/{id:[\da-zA-Z\-]+}'

    @response_schema(schema=ShopUnitSchema)
    async def get(self):
        unit_id = self.request.match_info['id']

        async with self.pg.begin() as conn:
            if not await ShopUnitStreamer.get_unit_record_by_id(unit_id, conn, None, None):
                raise HTTPNotFound()

        return Response(body=GetShopUnitQuery(unit_id, self.pg))
