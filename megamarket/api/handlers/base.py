from aiohttp.web_urldispatcher import View
from sqlalchemy.ext.asyncio import AsyncEngine


class BaseView(View):
    """
    Базовый обработчик, предоставляет удобный доступ к Engine'у
    """
    URL_PATH: str

    @property
    def pg(self) -> AsyncEngine:
        return self.request.app['pg']
