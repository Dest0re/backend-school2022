from aiohttp.web_exceptions import HTTPNotFound, HTTPOk
from aiohttp.web_response import Response
from aiohttp_apispec import match_info_schema

from .base import BaseView
from megamarket.db.schema import shop_unit_ids_table
from ..schema import IdMatchInfoRequestSchema


class DeleteView(BaseView):
    """
    Обработчик, реализующий доступ к удалению позиций.
    """
    URL_PATH = r'/delete/{id:[\da-zA-Z\-]+}'

    @match_info_schema(IdMatchInfoRequestSchema)
    async def delete(self):
        unit_id = self.request['match_info']['id']

        async with self.pg.execution_options(isolation_level='SERIALIZABLE').begin() as conn:
            query = shop_unit_ids_table.select().where(shop_unit_ids_table.c.id == unit_id)

            result = await conn.execute(query)
            if not result.first():
                raise HTTPNotFound()

            query = shop_unit_ids_table.delete().where(shop_unit_ids_table.c.id == unit_id)
            await conn.execute(query)

            await conn.commit()

        return Response(status=HTTPOk.status_code)
