import datetime
from http import HTTPStatus

import pytest

from megamarket.utils.pg import MAX_INTEGER
from megamarket.utils.testing import generate_offer, generate_category, generate_shop_units, import_data

LONGEST_STR = 'ё' * 256
CASES = [
    (
        [
            generate_offer(parent_id=None)
        ],
        HTTPStatus.OK,
    ),

    (
        [
            generate_category(unit_id='category-1'),
            generate_category(unit_id='category-2', parent_id='category-1'),
            generate_offer(unit_id='offer-1', parent_id='category-2'),
        ],
        HTTPStatus.OK,
    ),

    (
        generate_shop_units(count=1000, categories_count=100,
                            name=LONGEST_STR,
                            categories_name=LONGEST_STR,
                            price=MAX_INTEGER),
        HTTPStatus.OK,
    ),

    (
        [],
        HTTPStatus.OK,
    ),

    (
        [
            generate_offer(unit_id='offer-1'),
            generate_offer(unit_id='offer-2', parent_id='offer-1'),
        ],
        HTTPStatus.BAD_REQUEST
    ),

    (
        [
            generate_offer(unit_id='offer-1', parent_id='offer-2'),
        ],
        HTTPStatus.BAD_REQUEST
    ),

    (
        [
            generate_offer(unit_id='offer-1'),
            generate_offer(unit_id='offer-1'),
        ],
        HTTPStatus.BAD_REQUEST
    ),
]


@pytest.mark.parametrize('units,expected_status', CASES)
async def test_imports(api_client, units, expected_status):
    response = await import_data(
        api_client,
        units,
        expected_status=expected_status,
    )


async def test_future_request(api_client):
    response = await import_data(
        api_client,
        [],
        date=datetime.datetime(2030, 1, 1),
        expected_status=HTTPStatus.BAD_REQUEST,
    )


