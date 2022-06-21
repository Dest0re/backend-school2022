import time
from datetime import datetime
from enum import Enum
from typing import AsyncIterable, List

from asyncpg import Record
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncConnection

from megamarket.api.payloads import dumps
from megamarket.db.schema import shop_unit_revisions_table, relations_table, ShopUnitType


class EndOfStream:
    pass


class ShopUnitStreamer(AsyncIterable):
    @classmethod
    async def get_unit_record_by_id(cls, unit_id, pg: AsyncConnection,
                                    from_date: datetime | None,
                                    to_date: datetime | None) -> Record | None:
        query = (
            shop_unit_revisions_table
            .select()
            .where(shop_unit_revisions_table.c.shop_unit_id == unit_id)
            .order_by(shop_unit_revisions_table.c.date.desc())
            .limit(1)
        )

        if from_date is not None:
            query = query.where(shop_unit_revisions_table.c.date >= from_date)
        if to_date is not None:
            query = query.where(shop_unit_revisions_table.c.date <= to_date)

        result = await pg.execute(query)

        first = result.first()
        return first

    @classmethod
    async def get_parent_id_by_unit_id(cls, unit_id, pg: AsyncConnection,
                                       from_date: datetime | None,
                                       to_date: datetime | None) -> str | None:
        self_row = await cls.get_unit_record_by_id(unit_id, pg, from_date, to_date)

        if not self_row:
            raise KeyError()

        query = (
            relations_table
            .select()
            .where(relations_table.c.child_revision_id == self_row['id'])
            .limit(1)
        )
        result = await pg.execute(query)

        parent_row = result.first()
        return parent_row['parent_id'] if parent_row else None

    def __init__(self, unit_id, pg: AsyncConnection,
                 from_date: datetime | None = None,
                 to_date: datetime = datetime.now(),
                 stream_children=True):
        self._unit_id = unit_id
        self._pg = pg
        self._price = None
        self._date = None
        self._done = False
        self._stream_children = stream_children
        self._from_date = from_date
        self._to_date = to_date

    @property
    def price(self) -> int | None:
        if not self._done:
            raise Exception()

        return self._price

    @property
    def date(self) -> datetime | None:
        if not self._done:
            raise Exception()

        return self._date

    @property
    def children_count(self) -> int:
        raise NotImplementedError()

    @classmethod
    def type(cls) -> ShopUnitType:
        pass

    async def __aiter__(self):
        yield ''

        raise NotImplementedError()


class ShopOfferStreamer(ShopUnitStreamer):
    type = ShopUnitType.OFFER

    @property
    def price(self) -> int:
        return super(ShopOfferStreamer, self).price

    @property
    def children_count(self) -> int:
        return 1

    async def __aiter__(self):
        self_row = await self.get_unit_record_by_id(self._unit_id, self._pg,
                                                    self._from_date, self._to_date)

        if not self_row:
            raise KeyError

        parent_id = await self.get_parent_id_by_unit_id(self._unit_id, self._pg,
                                                        self._from_date, self._to_date)

        yield dumps({
            'id': self_row['shop_unit_id'],
            'name': self_row['name'],
            'date': self_row['date'],
            'type': self_row['type'],
            'price': self_row['price'],
            'parentId': parent_id,
            'children': None,
        })

        self._price = self_row['price']
        self._date = self_row['date']
        self._done = True

        yield EndOfStream()


class StreamerState(Enum):
    INITIALIZING = 0
    RUNNING = 1
    WAITING_FOR_CHILD = 2
    FINALIZING = 3
    DONE = 4


class ShopCategoryStreamer(ShopUnitStreamer):
    type = ShopUnitType.CATEGORY

    @property
    def children_count(self) -> int:
        return sum(child.children_count for child in self._children)

    @classmethod
    def get_children_ids_query(cls, unit_id,
                               from_date: datetime | None,
                               to_date: datetime | None):
        actual_revision_dates = (
            select([
                func.max(shop_unit_revisions_table.c.date).label('max_date'),
                shop_unit_revisions_table.c.shop_unit_id.label('child_id'),
            ])
            .group_by(shop_unit_revisions_table.c.shop_unit_id)
            .join(relations_table,
                  relations_table.c.child_revision_id == shop_unit_revisions_table.c.id,
                  isouter=True)
        )

        if from_date is not None:
            actual_revision_dates = actual_revision_dates.where(shop_unit_revisions_table.c.date >= from_date)
        if to_date is not None:
            actual_revision_dates = actual_revision_dates.where(shop_unit_revisions_table.c.date <= to_date)

        actual_revision_dates = actual_revision_dates.cte('actual_revision_dates', nesting=True)

        actual_parent_ids = (
            select([
                shop_unit_revisions_table.c.shop_unit_id.label('child_id'),
                shop_unit_revisions_table.c.type,
                relations_table.c.parent_id.label('parent_id'),
            ])
            .select_from(
                actual_revision_dates
                .join(
                    shop_unit_revisions_table,
                    (shop_unit_revisions_table.c.shop_unit_id == actual_revision_dates.c.child_id)
                    & (shop_unit_revisions_table.c.date == actual_revision_dates.c.max_date),
                    isouter=True
                )
                .join(
                    relations_table,
                    relations_table.c.child_revision_id == shop_unit_revisions_table.c.id,
                    isouter=True
                )
            )
        ).cte('actual_parent_ids')

        children_ids = (
            select([
                actual_parent_ids.c.child_id,
                actual_parent_ids.c.type,
            ])
            .where(actual_parent_ids.c.parent_id == unit_id)
        )

        return children_ids

    @classmethod
    async def get_children_ids(cls, unit_id, pg: AsyncConnection,
                               from_date: datetime | None,
                               to_date: datetime | None) -> List[Record]:

        result = await pg.execute(cls.get_children_ids_query(unit_id, from_date, to_date))
        return result.fetchall()

    def __init__(self, unit_id, pg: AsyncConnection,
                 from_date: datetime | None = None,
                 to_date: datetime | None = datetime.now()):
        super(ShopCategoryStreamer, self).__init__(unit_id, pg, from_date, to_date)
        self._state = StreamerState.INITIALIZING
        self._children = []
        self._children_done = -1
        self._price = None
        self._first = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        match self._state:
            case StreamerState.INITIALIZING:
                self_row = await self.get_unit_record_by_id(self._unit_id, self._pg,
                                                            self._from_date, self._to_date)

                if not self_row:
                    raise KeyError

                parent_id = await self.get_parent_id_by_unit_id(self._unit_id, self._pg,
                                                                self._from_date, self._to_date)

                for child_id, child_type in await self.get_children_ids(self._unit_id, self._pg,
                                                                        self._from_date, self._to_date):
                    self._children.append(shop_unit_streamer(child_type, child_id, self._pg,
                                                             self._from_date, self._to_date))

                self._state = StreamerState.RUNNING

                self._date = self_row['date']

                return dumps({
                    'id': self_row['shop_unit_id'],
                    'name': self_row['name'],
                    'type': self_row['type'],
                    'parentId': parent_id,
                })[:-1] + (', "children": [' if self._stream_children else '')

            case StreamerState.RUNNING:
                self._children_done += 1

                if self._children_done == len(self._children):
                    self._state = StreamerState.FINALIZING
                    return ''
                else:
                    self._state = StreamerState.WAITING_FOR_CHILD
                    return self._children[self._children_done]

            case StreamerState.WAITING_FOR_CHILD:
                child_price = self._children[self._children_done].price

                if self._price is None:
                    self._price = child_price
                else:
                    self._price += child_price

                self._state = StreamerState.RUNNING

                if self._children_done != len(self._children) - 1:
                    return ', '
                else:
                    return ''

            case StreamerState.FINALIZING:
                self._state = StreamerState.DONE
                self._date = max(self._date,
                                 max((child.date for child in self._children), default=self._date))

                if not self._children:
                    price = None
                else:
                    price = self._price // self.children_count

                return (']' if self._stream_children else '') + ', ' + dumps({
                    'price': price,
                    'date': self._date,
                })[1:]

            case StreamerState.DONE:
                if not self._done:
                    self._done = True
                    return EndOfStream()
                else:
                    raise StopAsyncIteration


def shop_unit_streamer(unit_type, unit_id, pg: AsyncConnection,
                       from_date: datetime | None,
                       to_date: datetime | None,
                       stream_children=True
                       ) -> ShopUnitStreamer:
    match unit_type:
        case ShopUnitType.OFFER:
            return ShopOfferStreamer(unit_id, pg, from_date, to_date, stream_children=stream_children)
        case ShopUnitType.CATEGORY:
            return ShopCategoryStreamer(unit_id, pg, from_date, to_date)


def shop_unit_streamer_from_record(unit_record, pg: AsyncConnection,
                                   from_date: datetime | None,
                                   to_date: datetime | None,
                                   stream_children=True,
                                   ) -> ShopUnitStreamer:
    return shop_unit_streamer(unit_record['type'], unit_record['shop_unit_id'], pg,
                              from_date, to_date, stream_children=stream_children)


async def do_stream(streamer):
    stack = [streamer]
    while stack:
        async for data in stack[-1]:
            if issubclass(type(data), ShopUnitStreamer):
                stack.append(data)
                break
            elif isinstance(data, EndOfStream):
                stack.pop()
            else:
                yield data
