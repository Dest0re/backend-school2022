from datetime import datetime
from http import HTTPStatus

import pytest

from megamarket.utils.testing import generate_offer, generate_response_offer, get_unit, import_data, \
    normalize_response_unit, generate_category, generate_response_category, compare_units

date = datetime.now()

CASES = [
    # Один оффер
    (
        'offer-1',
        [
            generate_offer(unit_id='offer-1', name='offer-1', price=19999)
        ],
        generate_response_offer(unit_id='offer-1', name='offer-1', price=19999, date=date)
    ),

    # Многократная вложенность
    (
        'category-1',
        [
            generate_category(unit_id='category-1', name='category-1'),
            generate_category(unit_id='category-2', name='category-2', parent_id='category-1'),
            generate_offer(unit_id='offer-1', name='offer-1', parent_id='category-2', price=19999)
        ],
        generate_response_category(
            unit_id='category-1', name='category-1', date=date,
            children=[
                generate_response_category(
                    unit_id='category-2', name='category-2', date=date, parent_id='category-1',
                    children=[
                        generate_response_offer(
                            unit_id='offer-1', name='offer-1', date=date, parent_id='category-2', price=19999
                        )
                    ]
                )
            ])
    ),

    # Пустая категория
    (
        'category-1',
        [
            generate_category(unit_id='category-1', name='category-1'),
        ],
        generate_response_category(unit_id='category-1', name='category-1', date=date)
    )
]


@pytest.mark.parametrize('offer_id,units,expected_unit', CASES)
async def test_get_nodes(api_client, offer_id, units, expected_unit):
    await import_data(api_client, units, date=date)

    resp = await get_unit(api_client, offer_id)

    resp = normalize_response_unit(resp)

    assert compare_units(resp, expected_unit)


async def test_404_error(api_client):
    await get_unit(api_client, 'nothing', expected_status=HTTPStatus.NOT_FOUND)
