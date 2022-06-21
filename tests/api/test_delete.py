from http import HTTPStatus

from megamarket.utils.testing import import_data, generate_offer, delete_unit


async def test_delete(api_client):
    await import_data(api_client, [generate_offer(unit_id='1')])

    await delete_unit(api_client, '1', HTTPStatus.OK)

    await delete_unit(api_client, '1', HTTPStatus.NOT_FOUND)
