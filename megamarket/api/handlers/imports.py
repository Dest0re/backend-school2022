from datetime import datetime
from typing import Generator

import asyncpg
import sqlalchemy
from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPBadRequest, HTTPOk
from aiohttp_apispec.decorators import request_schema
from aiomisc import chunk_list
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql import func

from megamarket.api.schema import ShopUnitImportRequestSchema
from megamarket.db.schema import relations_table, shop_unit_revisions_table, shop_unit_ids_table
from megamarket.utils.pg import max_query_len_with
from .base import BaseView


class ImportsView(BaseView):
    URL_PATH = '/imports'

    MAX_UNIT_IDS_PER_INSERT = max_query_len_with(len(shop_unit_ids_table.columns))
    MAX_UNIT_REVISIONS_PER_INSERT = max_query_len_with(len(shop_unit_revisions_table.columns))
    MAX_RELATIONS_PER_INSERT = max_query_len_with(len(relations_table.columns))
    MAX_SINGLE_ROW_WHERE = max_query_len_with(1)

    @classmethod
    def make_shop_units_ids_rows(cls, units):
        for unit in units:
            yield {
                'id': unit['id'],
            }

    @classmethod
    def make_units_table_rows(cls, units, update_date) -> Generator:
        for unit in units:
            yield {
                'shop_unit_id': unit['id'],
                'name': unit['name'],
                'price': unit['price'] if 'price' in unit else None,
                'date': update_date,
                'type': unit['type'],
            }

    @classmethod
    def get_revision_ids_query(cls, unit_ids):
        actual_revision_dates = (
            select([
                shop_unit_revisions_table.c.shop_unit_id,
                func.max(shop_unit_revisions_table.c.date).label('max_date')
            ])
            .group_by(shop_unit_revisions_table.c.shop_unit_id)
            .cte('actual_revision_dates')
        )

        actual_revision_ids = (
            select([
                actual_revision_dates.c.shop_unit_id,
                shop_unit_revisions_table.c.id,
            ])
            .where(
                (actual_revision_dates.c.shop_unit_id == shop_unit_revisions_table.c.shop_unit_id) &
                (actual_revision_dates.c.max_date == shop_unit_revisions_table.c.date),
            )
        )

        query = (
            actual_revision_ids
            .where(shop_unit_revisions_table.c.shop_unit_id.in_(unit_ids))
        )

        return query

    @classmethod
    async def insert_revisions(cls, units, date, pg: AsyncConnection):
        unit_revision_rows = cls.make_units_table_rows(units, date)

        chunked_unit_rows = chunk_list(unit_revision_rows,
                                       cls.MAX_UNIT_REVISIONS_PER_INSERT)

        insert_statement = shop_unit_revisions_table.insert()

        for chunk in chunked_unit_rows:
            await pg.execute(insert_statement, list(chunk))

    @classmethod
    async def make_relations_table_rows(cls, units, pg: AsyncConnection):
        relations = [(unit['id'], unit['parentId'])
                     for unit in units if 'parentId' in unit and unit['parentId'] is not None]
        chunked_children_ids = chunk_list(relations, cls.MAX_SINGLE_ROW_WHERE)

        relation_rows = []

        for chunk in chunked_children_ids:
            relations_dict = {c[0]: c[1] for c in chunk}

            query = cls.get_revision_ids_query(relations_dict.keys())
            result = await pg.execute(query)
            revision_ids = result.fetchall()

            for child_id, child_revision_id in revision_ids:
                relation_rows.append({
                    'parent_id': relations_dict[child_id],
                    'child_revision_id': child_revision_id,
                })

        return relation_rows

    @request_schema(schema=ShopUnitImportRequestSchema)
    async def post(self):
        params = self.request['data']

        if 'items' not in params or not params['items']:
            return Response(status=HTTPOk.status_code)

        units = params['items']

        if 'updateDate' not in params:
            update_date = datetime.now()
        else:
            update_date = params['updateDate']

        async with self.pg.execution_options(isolation_level='SERIALIZABLE').begin() as conn:
            shop_unit_ids_rows = self.make_shop_units_ids_rows(units)
            shop_unit_revisions_rows = self.make_units_table_rows(units, update_date)

            chunked_unit_ids_rows = chunk_list(shop_unit_ids_rows,
                                               self.MAX_UNIT_IDS_PER_INSERT)
            chunked_unit_revisions_rows = chunk_list(shop_unit_revisions_rows,
                                                     self.MAX_UNIT_REVISIONS_PER_INSERT)

            insert_statement = insert(shop_unit_ids_table).on_conflict_do_nothing()
            for chunk in chunked_unit_ids_rows:
                await conn.execute(insert_statement.values(list(chunk)))

            try:
                insert_statement = shop_unit_revisions_table.insert()
                for chunk in chunked_unit_revisions_rows:
                    await conn.execute(insert_statement.values(list(chunk)))
            except sqlalchemy.exc.IntegrityError:
                raise HTTPBadRequest()
            except sqlalchemy.exc.DBAPIError as e:
                if e.orig.sqlstate == asyncpg.exceptions.RaiseError.sqlstate:
                    raise HTTPBadRequest()

                raise

            try:
                relation_rows = await self.make_relations_table_rows(units, conn)
                chunked_relation_rows = chunk_list(relation_rows, self.MAX_RELATIONS_PER_INSERT)

                insert_statement = relations_table.insert()
                for chunk in chunked_relation_rows:
                    await conn.execute(insert_statement.values(list(chunk)))
            except asyncpg.exceptions.RaiseError:
                raise HTTPBadRequest()
            except sqlalchemy.exc.IntegrityError:
                raise HTTPBadRequest()
            except sqlalchemy.exc.DBAPIError as e:
                if e.orig.sqlstate == asyncpg.exceptions.ObjectNotInPrerequisiteStateError.sqlstate:
                    raise HTTPBadRequest()

                raise

            await conn.commit()

        return Response(status=HTTPOk.status_code)
