from aiohttp.web import Response

from .base import BaseView


class EchoView(BaseView):
    URL_PATH = '/echo'

    async def post(self):
        params = await self.fetch_json()

        print(params['parent_id'])

        return Response(body=self.request.query_string)
