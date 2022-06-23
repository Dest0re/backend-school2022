import asyncio
import time
from collections.abc import AsyncIterable
from datetime import datetime

from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp_apispec import match_info_schema, querystring_schema
from aiohttp_apispec.decorators import response_schema
from aiomisc import chunk_list
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection

from megamarket.api.schema import ShopUnitSchema, ShopUnitStatisticsRequestParamsSchema, \
    IdMatchInfoRequestSchema
from .base import BaseView
from ...db.schema import ShopUnitType, shop_unit_revisions_table
from ...utils.pg import max_query_len_with
from ...utils.streamers import ShopUnitStreamer, ShopCategoryStreamer, \
    shop_unit_streamer_from_record, do_stream


class GetNodeStatistic(AsyncIterable):
    def __init__(self, unit_id: str,
                 pg: AsyncEngine,
                 timeout: int = None,
                 from_date: datetime | None = None,
                 to_date: datetime | None = datetime.now()):
        self._unit_id = unit_id
        self._pg = pg
        self._timeout = timeout
        self._from_date = from_date
        self._to_date = to_date

    @classmethod
    def get_revisions_query(cls, unit_ids, from_date: datetime | None, to_date: datetime | None):
        query = shop_unit_revisions_table.select().where(
            shop_unit_revisions_table.c.shop_unit_id.in_(unit_ids)
        )
        if from_date:
            query = query.where(shop_unit_revisions_table.c.date >= from_date)
        if to_date:
            query = query.where(shop_unit_revisions_table.c.date <= to_date)

        return query

    @classmethod
    async def get_update_dates(cls, unit_id, from_date, to_date, conn: AsyncConnection):
        stack = [unit_id]
        relevant_ids = {unit_id}
        update_dates = set()

        while stack:
            unit_id = stack.pop()
            children = await ShopCategoryStreamer.get_children_ids(
                unit_id, conn, from_date, to_date
            )

            for child in children:
                if child['type'] == ShopUnitType.CATEGORY:
                    stack.append(child['child_id'])

                relevant_ids.add(child['child_id'])

        maximum_ids_per_query = max_query_len_with(1) - 2

        chunked_ids = chunk_list(relevant_ids, maximum_ids_per_query)

        for chunk in chunked_ids:
            query = cls.get_revisions_query(list(chunk), from_date, to_date)
            for row in await conn.execute(query):
                update_dates.add(row['date'])

        return sorted(list(update_dates))

    async def __aiter__(self):
        yield '{"items": ['
        async with self._pg.begin() as conn:
            update_dates = await self.get_update_dates(
                self._unit_id, self._from_date, self._to_date, conn)

            first = True
            for date in update_dates:
                if not first:
                    yield ', '
                else:
                    first = False

                unit = await ShopUnitStreamer.get_unit_record_by_id(self._unit_id, conn, None, date)

                if not unit:
                    continue

                unit_streamer = shop_unit_streamer_from_record(unit, conn, None, date,
                                                               stream_children=False)

                exec_time = time.time()
                async for chunk in do_stream(unit_streamer):
                    if self._timeout and time.time() - exec_time > self._timeout:
                        raise asyncio.TimeoutError

                    yield chunk

        yield ']}'


class NodeView(BaseView):
    URL_PATH = r'/node/{id:[\da-zA-Z\-]+}/statistic'

    @match_info_schema(IdMatchInfoRequestSchema)
    @querystring_schema(ShopUnitStatisticsRequestParamsSchema)
    @response_schema(schema=ShopUnitSchema)
    async def get(self):
        unit_id = self.request['match_info']['id']
        querystring = self.request['querystring']
        date_start = querystring['dateStart'] if 'dateStart' in querystring else None
        date_end = querystring['dateEnd'] if 'dateEnd' in querystring else None

        async with self.pg.begin() as conn:
            if not await ShopUnitStreamer.get_unit_record_by_id(unit_id, conn, None, None):
                raise HTTPNotFound()

        return Response(
            body=GetNodeStatistic(unit_id, self.pg, 10, date_start, date_end)
        )
