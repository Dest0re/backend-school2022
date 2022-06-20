from json import JSONDecodeError

from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_urldispatcher import View
from asyncpgsa import PG
from sqlalchemy.ext.asyncio import AsyncEngine


class BaseView(View):
    URL_PATH: str

    @property
    def pg(self) -> AsyncEngine:
        return self.request.app['pg']

    async def fetch_json(self):
        try:
            return await self.request.json()
        except JSONDecodeError:
            raise HTTPBadRequest()
