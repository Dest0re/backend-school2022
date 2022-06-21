import asyncio
import time
from collections.abc import AsyncIterable
from datetime import datetime, timedelta

from aiohttp.web import Response
from aiohttp_apispec.decorators import response_schema
from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncEngine

from .base import BaseView
from megamarket.api.schema import ShopUnitStatisticResponseSchema, SalesRequestParamsSchema
from ...db.schema import shop_unit_revisions_table, ShopUnitType
from ...utils.streamers import ShopUnitStreamer, shop_unit_streamer_from_record, do_stream


class GetSalesQuery(AsyncIterable):
    @classmethod
    def get_revisions(cls, date_from: datetime | None, date_to: datetime | None):
        query = (
            select([
                shop_unit_revisions_table.c.shop_unit_id,
                func.max_(shop_unit_revisions_table.c.date).label('max_date'),
                shop_unit_revisions_table.c.type
            ])
            .group_by(shop_unit_revisions_table.c.shop_unit_id,
                      shop_unit_revisions_table.c.type)
        )

        if date_from is not None:
            query = query.where(shop_unit_revisions_table.c.date >= date_from)
        if date_to is not None:
            query = query.where(shop_unit_revisions_table.c.date <= date_to)

        return query

    def __init__(self,
                 pg: AsyncEngine,
                 timeout: int = None,
                 from_date: datetime | None = None,
                 to_date: datetime | None = datetime.now()):
        self.pg = pg
        self.timeout = timeout
        self._from_date = from_date
        self._to_date = to_date

    async def __aiter__(self):
        yield '{"items": ['

        async with self.pg.begin() as conn:
            get_revisions_query = self.get_revisions(self._from_date, self._to_date)\
                .where(shop_unit_revisions_table.c.type == ShopUnitType.OFFER)
            result = await conn.execute(get_revisions_query)

            exec_time = time.time()
            first = True
            for revision in result.fetchall():
                if not first:
                    yield ', '
                else:
                    first = False

                unit = shop_unit_streamer_from_record(revision, conn,
                                                      self._from_date, self._to_date,
                                                      stream_children=False)

                async for chunk in do_stream(unit):
                    if self.timeout and time.time() - exec_time > self.timeout:
                        raise asyncio.TimeoutError()

                    yield chunk

        yield ']}'


class SalesView(BaseView):
    URL_PATH = r'/sales'

    @response_schema(schema=ShopUnitStatisticResponseSchema)
    async def get(self):
        params = SalesRequestParamsSchema().load(self.request.query)

        to_date = params['date']
        from_date = to_date - timedelta(days=1)

        return Response(
            body=GetSalesQuery(
                self.pg, timeout=10, from_date=from_date, to_date=to_date
            )
        )
