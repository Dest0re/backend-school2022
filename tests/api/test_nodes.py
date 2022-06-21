from datetime import datetime, timedelta
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
    ),

    # Категория с двумя товарами
    (
        'category-1',
        [
            generate_category(unit_id='category-1', name='category-1'),
            generate_offer(unit_id='offer-1', name='offer-1', price='20', parent_id='category-1'),
            generate_offer(unit_id='offer-2', name='offer-2', price='10', parent_id='category-1'),
        ],
        generate_response_category(
            unit_id='category-1', name='category-1', date=date,
            children=[
                generate_response_offer(unit_id='offer-1', name='offer-1', price=20, parent_id='category-1', date=date),
                generate_response_offer(unit_id='offer-2', name='offer-2', price=10, parent_id='category-1', date=date),
            ]
        )
    ),

    # Товары разной вложенности, корневая директория должна верно расчитать стоимость
    (
        'category-1',
        [
            generate_category(unit_id='category-1', name='category-1'),
            generate_offer(unit_id='offer-1', name='offer-1', parent_id='category-1', price=30),
            generate_category(unit_id='category-2', name='category-2', parent_id='category-1'),
            generate_offer(unit_id='offer-2', name='offer-2', parent_id='category-2', price=10),
        ],
        generate_response_category(
            unit_id='category-1', name='category-1', date=date,
            children=[
                generate_response_offer(
                    unit_id='offer-1', name='offer-1', date=date, parent_id='category-1', price=30,
                ),
                generate_response_category(
                    unit_id='category-2', name='category-2', date=date, parent_id='category-1',
                    children=[
                        generate_response_offer(
                            unit_id='offer-2', name='offer-2', date=date, parent_id='category-2', price=10
                        )
                    ]
                )
            ]
        )
    ),
]


@pytest.mark.parametrize('offer_id,units,expected_unit', CASES)
async def test_get_nodes(api_client, offer_id, units, expected_unit):
    await import_data(api_client, units, date=date)

    resp = await get_unit(api_client, offer_id)

    assert compare_units(resp, expected_unit)


async def test_404_error(api_client):
    await get_unit(api_client, 'nothing', expected_status=HTTPStatus.NOT_FOUND)


async def test_node_update(api_client):
    unit1 = [generate_offer(unit_id='1', name='1', price=123321)]
    unit2 = [generate_offer(unit_id='1', name='2', price=321123)]

    await import_data(api_client, unit1, date - timedelta(hours=1))
    await import_data(api_client, unit2, date)

    expected_unit = generate_response_offer(unit_id='1', name='2', price=321123, date=date)

    resp = await get_unit(api_client, '1')

    assert compare_units(expected_unit, resp)
