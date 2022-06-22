import datetime
from http import HTTPStatus

import pytest

from megamarket.utils.testing import generate_offer, generate_response_offer, import_data, get_node_statistic, \
    compare_unit_lists, generate_category, generate_response_category

date = datetime.datetime.now()

CASES = [
    (
        'o-1',
        [
            (
                [
                    generate_offer(unit_id='o-1', name='o-1', price=123),
                ],
                date
            ),
        ],
        [
            generate_response_offer(unit_id='o-1', name='o-1', price=123, date=date, include_children=False)
        ]
    ),
    (
        'o-1',
        [
            (
                [
                    generate_offer(unit_id='o-1', name='o-1', price=123),
                ],
                date - datetime.timedelta(hours=3)
            ),
            (
                [
                    generate_offer(unit_id='o-1', name='o-1', price=246),
                ],
                date - datetime.timedelta(hours=2)
            ),
            (
                [
                    generate_offer(unit_id='o-1', name='o-2', price=246),
                ],
                date - datetime.timedelta(hours=1)
            )
        ],
        [
            generate_response_offer(unit_id='o-1', name='o-1', price=123, date=date - datetime.timedelta(hours=3), include_children=False),
            generate_response_offer(unit_id='o-1', name='o-1', price=246, date=date - datetime.timedelta(hours=2), include_children=False),
            generate_response_offer(unit_id='o-1', name='o-2', price=246, date=date - datetime.timedelta(hours=1), include_children=False),
        ]
    ),
    (
        'c-1',
        [
            (
                [
                    generate_category(unit_id='c-1', name='c-1')
                ],
                date - datetime.timedelta(hours=3)
            ),
            (
                [
                    generate_offer(unit_id='o-1', name='o-1', parent_id='c-1', price=123321)
                ],
                date - datetime.timedelta(hours=2),
            ),
            (
                [
                    generate_offer(unit_id='o-1', name='o-2', parent_id='c-1', price=123321)
                ],
                date - datetime.timedelta(hours=1)
            ),
        ],
        [
            generate_response_category(
                unit_id='c-1', name='c-1', date=date - datetime.timedelta(hours=3), include_children=False
            ),
            generate_response_category(
                unit_id='c-1', name='c-1', date=date - datetime.timedelta(hours=2), include_children=False,
                children=[
                    generate_response_offer(unit_id='o-1', date=date - datetime.timedelta(hours=2), price=123321)
                ]
            ),
            generate_response_category(
                unit_id='c-1', name='c-1', date=date - datetime.timedelta(hours=1), include_children=False,
                children=[
                    generate_response_offer(unit_id='o-1', date=date - datetime.timedelta(hours=1), price=123321)
                ]
            ),
        ]
    )
]


@pytest.mark.parametrize('unit_id,unit_groups,expected_units', CASES)
async def test_node_statistic(api_client, unit_id, unit_groups, expected_units):
    for units, group_date in unit_groups:
        await import_data(api_client, units, date=group_date)

    resp = await get_node_statistic(api_client, unit_id)

    assert compare_unit_lists(resp, expected_units)


async def test_404_error(api_client):
    await get_node_statistic(api_client, '-', None, None, HTTPStatus.NOT_FOUND)
