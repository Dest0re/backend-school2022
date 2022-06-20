from aiohttp.web_exceptions import HTTPNotFound, HTTPOk
from aiohttp.web_response import Response

from .base import BaseView
from megamarket.db.schema import shop_unit_ids_table


class DeleteView(BaseView):
    URL_PATH = r'/delete/{id:[\da-zA-Z\-]+}'

    async def delete(self):
        unit_id = self.request.match_info['id']

        async with self.pg.begin() as conn:#isolation='serializable'):
            query = shop_unit_ids_table.select().where(shop_unit_ids_table.c.id == unit_id)

            result = await conn.execute(query)
            if not result.first():
                raise HTTPNotFound()

            query = shop_unit_ids_table.delete().where(shop_unit_ids_table.c.id == unit_id)
            await conn.execute(query)

            await conn.commit()

        return Response(status=HTTPOk.status_code)
