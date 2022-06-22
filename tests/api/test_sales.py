import datetime

from megamarket.utils.testing import generate_offer, generate_response_offer, get_sales, import_data, compare_unit_lists

date = datetime.datetime.now()

CASES = [
    (
        [

        ],
        [

        ]
    )
]


async def test_single_sale(api_client):
    unit = [generate_offer(unit_id='1', name='1', price=123321)]

    await import_data(api_client, unit, date)

    resp = await get_sales(api_client, date)

    expected_unit = [generate_response_offer(unit_id='1', name='1', price=123321, date=date, include_children=False)]

    assert compare_unit_lists(resp, expected_unit)


async def test_multiple_sales(api_client):
    unit1 = [generate_offer(unit_id='1', name='1', price=123321)]
    unit2 = [generate_offer(unit_id='2', name='2', price=123321)]

    await import_data(api_client, unit1, date)
    await import_data(api_client, unit2, date - datetime.timedelta(hours=1))

    resp = await get_sales(api_client, date)

    expected_units = [
        generate_response_offer(unit_id='1', name='1', price=123321, date=date, include_children=False),
        generate_response_offer(unit_id='2', name='2', price=123321, date=date - datetime.timedelta(hours=1),
                                include_children=False)
    ]

    assert compare_unit_lists(resp, expected_units)


async def test_without_sales(api_client):
    unit = [generate_offer(unit_id='1', name='1', price=123321)]

    await import_data(api_client, unit, date - datetime.timedelta(days=1, seconds=1))

    resp = await get_sales(api_client, date)

    expected_units = []

    assert compare_unit_lists(resp, expected_units)


async def test_duplicate_update(api_client):
    unit = [generate_offer(unit_id='1', name='1', price=123321)]

    await import_data(api_client, unit, date - datetime.timedelta(hours=1))
    await import_data(api_client, unit, date)

    resp = await get_sales(api_client, date)

    expected_units = [
        generate_response_offer(unit_id='1', name='1', price=123321, date=date, include_children=False),
    ]

    assert compare_unit_lists(resp, expected_units)
