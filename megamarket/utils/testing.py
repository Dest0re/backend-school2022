import datetime
import json
import logging
import math
import random
import uuid
from enum import EnumMeta
from http import HTTPStatus

from aiohttp.test_utils import TestClient
from aiohttp.web_urldispatcher import DynamicResource

from megamarket.api.handlers import ImportsView, NodeView, NodesView, DeleteView, SalesView
from megamarket.api.schema import DATETIME_FORMAT, ShopUnitSchema, ShopUnitStatisticResponseSchema

COMPANIES = [
    'Pineapple',
    'Samson',
    'Xiamio',
    'RaidMe',
    'OneMinus',
    'Gogle',
    'Meisu',
    'Sonic',
    'Sasio',
    'Arthas',
    'Inoi',
    'Kono',
]

DEVICE_NAMES = [
    'Phone',
    'UPhone',
    'Smartphone',
    'Tablet',
    'Tab',
    'Table',
    'Tabloid',
    'Laptop',
    'Lapbottom',
    'Book',
    'Notebook',
    'Note',
    'TV',
    'TVSet',
    'TVScreen',
    'Screen',
]

DEVICE_VERSIONS = [
    *range(1, 30),
    *range(2020, 2030),
    *range(2000, 10000, 1000),
]

VERSION_MODIFIERS = [
    'PRO',
    'Plus',
    'ULTRA',
    'PRO',
    'MEGA',
    'A',
    'S',
    'D',
]

categories = [
    'Phones',
    'Tablets',
    'Laptops',
    'Books',
    'TVs',
    'Monitors',
    'PCs',
    'Accessories',
]

CATEGORIES = []

for n in range(2020, 2030):
    CATEGORIES.extend(f'{category} {n}' for category in categories)


def url_for(path: str, **kwargs) -> str:
    kwargs = {
        key: str(value)
        for key, value in kwargs.items()
    }
    return str(DynamicResource(path).url_for(**kwargs))


def generate_device_name():
    name = '{} {} {}'.format(
        random.choice(COMPANIES),
        random.choice(DEVICE_NAMES),
        random.choice(DEVICE_VERSIONS)
    )

    for _ in range(random.randint(0, 3)):
        name += ' '
        name += random.choice(VERSION_MODIFIERS)

    return name


def generate_category_name():
    return CATEGORIES.pop(random.randint(0, len(CATEGORIES) - 1))


def generate_shop_unit(
        unit_id=None,
        name=None,
        unit_type=None,
        parent_id=None,
        price=None,
):
    if unit_id is None:
        unit_id = str(uuid.uuid4())

    if unit_type is None:
        unit_type = random.choice(['CATEGORY', 'OFFER'])

    if name is None:
        match unit_type:
            case 'CATEGORY':
                name = generate_category_name()
            case 'OFFER':
                name = generate_device_name()

    if parent_id is None:
        parent_id = None

    if price is None:
        price = None

    return {
        'id': unit_id,
        'name': name,
        'type': unit_type,
        'parentId': parent_id,
        'price': price,
    }


def generate_offer(
        unit_id=None,
        name=None,
        parent_id=None,
        price=None,
):
    if price is None:
        price = random.choice(range(1000, 500000, 100)) - 1

    return generate_shop_unit(
        unit_id=unit_id,
        name=name,
        unit_type='OFFER',
        parent_id=parent_id,
        price=price,
    )


def generate_category(
        unit_id=None,
        name=None,
        parent_id=None,
):
    return generate_shop_unit(
        unit_id=unit_id,
        name=name,
        unit_type='CATEGORY',
        parent_id=parent_id,
        price=None,
    )


def generate_categories(
        count=None,
        nesting=None,
        name=None,
):
    if count is None:
        count = random.randint(10, 20)

    if nesting is None:
        nesting = count // 5

    nested_categories = [[] for _ in range(nesting)]

    for i, category in enumerate(nested_categories):
        for _ in range(random.randint(1, math.ceil(count / nesting))):
            category.append(generate_category(
                name=name,
                parent_id=None if i == 0 else random.choice(nested_categories[i-1])['id'],
            ))

    flat_categories = []
    for category in nested_categories:
        flat_categories.extend(category)

    return flat_categories


def generate_shop_units(
        count=None,
        without_categories=None,
        nesting=None,
        categories_count=None,
        name=None,
        categories_name=None,
        price=None,
        parent_id=None,
):
    if count is None:
        count = random.randint(1, 10)

    if nesting is None:
        nesting = count // 5

    categories = generate_categories(
        count=categories_count,
        nesting=nesting,
        name=categories_name,
    )

    units = []

    if without_categories:
        for _ in range(without_categories):
            count -= 1

            unit = generate_offer(
                name=name,
                parent_id=None,
                price=price,
            )

            units.append(unit)

    for _ in range(count):
        unit = generate_offer(
            name=name,
            parent_id=random.choice(categories)['id'] if not parent_id else parent_id,
        )

        units.append(unit)

    categories.extend(units)

    return categories


async def import_data(
        client: TestClient,
        units: list,
        date: datetime.datetime | None = None,
        expected_status: int | EnumMeta = HTTPStatus.OK,
        **request_kwargs
):
    if date is None:
        date = datetime.datetime.now()

    request_data = {
        'items': units,
        'updateDate': date.strftime(DATETIME_FORMAT),
    }

    response = await client.post(
        ImportsView.URL_PATH,
        json=request_data,
        **request_kwargs
    )
    assert response.status == expected_status


async def delete_unit(
        client: TestClient,
        unit_id: str,
        expected_status: int | EnumMeta = HTTPStatus.OK,
        **request_kwargs
):
    response = await client.delete(
        url_for(
            DeleteView.URL_PATH,
            id=unit_id,
        ),
        **request_kwargs
    )
    assert response.status == expected_status


async def get_unit(
        client: TestClient,
        unit_id: str,
        expected_status: int | EnumMeta = HTTPStatus.OK,
        **request_kwargs
):
    response = await client.get(
        url_for(NodesView.URL_PATH, id=unit_id),
        **request_kwargs)

    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        data = await response.json()

        errors = ShopUnitSchema().validate(data)

        assert not errors

        return data


async def get_sales(
        client: TestClient,
        date: datetime.datetime | None = None,
        expected_status: int | EnumMeta = HTTPStatus.OK,
        **request_kwargs
):
    if date is None:
        date = datetime.datetime.now()

    response = await client.get(
        SalesView.URL_PATH,
        params={
            'date': date.strftime(DATETIME_FORMAT),
        },
        **request_kwargs
    )

    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        data = await response.json()

        errors = ShopUnitStatisticResponseSchema().validate(data)

        assert not errors

        return data['items']


async def get_node_statistic(
        client: TestClient,
        unit_id: str,
        date_start: datetime.datetime | None = None,
        date_end: datetime.datetime | None = None,
        expected_status: int | EnumMeta = HTTPStatus.OK,
        **request_kwargs
):
    params = {}
    if date_start is not None:
        params['date_start'] = date_start.strftime(DATETIME_FORMAT)

    if date_end is not None:
        params['date_end'] = date_end.strftime(DATETIME_FORMAT)

    response = await client.get(
        url_for(
            NodeView.URL_PATH,
            id=unit_id,
        ),
        params=params,
        **request_kwargs
    )

    assert response.status == expected_status

    if expected_status == HTTPStatus.OK:
        data = await response.json()

        errors = ShopUnitStatisticResponseSchema().validate(data)

        assert not errors

        return data['items']


class ResponseUnit:
    def __init__(
            self,
            unit_id: str = None,
            name: str = None,
            date: datetime.datetime | None = None,
            price: int | None = None,
            parent_id: str | None = None,
            unit_type: str | None = None,
            children: list | None = None,
            include_children: bool = True,
            children_count: int | None = None
    ):
        self.unit_id = unit_id or str(uuid.uuid4())

        self.name = name or f'Unit {unit_id}'

        self.date = date or datetime.datetime.now()

        self.price = price

        self.parent_id = parent_id

        self.unit_type = unit_type or random.choice(['CATEGORY', 'OFFER'])

        self.children = children

        self.include_children = include_children

        self.children_count = children_count or 1

    def json(self):
        raise NotImplementedError

    def __str__(self):
        return json.dumps(self.json(), ensure_ascii=False, indent=2)

    def __repr__(self):
        return self.__str__()


class ResponseOffer(ResponseUnit):
    def __init__(
            self,
            unit_id: str = None,
            name: str = None,
            date: datetime.datetime | None = None,
            price: int | None = None,
            parent_id: str | None = None,
            include_children: bool = True,
    ):
        if unit_id is None:
            unit_id or str(uuid.uuid4())

        if name is None:
            name = generate_device_name()

        if date is None:
            date = datetime.datetime.now()

        if price is None:
            price = random.choice(range(1000, 100000, 100)) - 1

        if parent_id is None:
            parent_id = parent_id

        self.include_children = include_children

        self.unit_type = 'OFFER'

        self.children = None

        children_count = 1

        super(ResponseOffer, self).__init__(
            unit_id=unit_id,
            name=name,
            date=date,
            price=price,
            parent_id=parent_id,
            unit_type=self.unit_type,
            children=None,
            include_children=include_children,
            children_count=children_count
        )

    def json(self):
        data = {
            'id': self.unit_id,
            'name': self.name,
            'date': self.date.strftime(DATETIME_FORMAT),
            'price': self.price,
            'parentId': self.parent_id,
            'type': self.unit_type,
        }

        if self.include_children:
            data['children'] = None

        return data


class ResponseCategory(ResponseUnit):
    def __init__(
            self,
            unit_id: str = None,
            name: str = None,
            date: datetime.datetime | None = None,
            parent_id: str | None = None,
            children: list | None = None,
            include_children: bool = True
    ):
        if unit_id is None:
            unit_id = str(uuid.uuid4())

        if name is None:
            name = generate_device_name()

        if date is None:
            date = datetime.datetime.now()

        if children is None:
            children = []

        for child in children:
            if child.date > date:
                date = child.date

        unit_type = 'CATEGORY'

        if children:
            children_count = sum(child.children_count for child in children)
            price = sum(child.price for child in children)
        else:
            children_count = 0
            price = None

        super(ResponseCategory, self).__init__(
            unit_id=unit_id,
            name=name,
            date=date,
            parent_id=parent_id,
            unit_type=unit_type,
            children=children,
            include_children=include_children,
            price=price,
            children_count=children_count,
        )

    def json(self):
        self_json = {
            'id': self.unit_id,
            'name': self.name,
            'date': self.date.strftime(DATETIME_FORMAT),
            'parentId': self.parent_id,
            'type': self.unit_type,
        }

        if self.children:
            self_json['price'] = self.price // self.children_count
        else:
            self_json['price'] = None

        if self.include_children:
            if self.children:
                self_json['children'] = normalize_response_units(self.children)
            else:
                self_json['children'] = []

        return self_json


def generate_response_unit(
        unit_id: str = None,
        name: str = None,
        date: datetime.datetime | None = None,
        price: int | None = None,
        parent_id: str | None = None,
        unit_type: str | None = None,
        children: list | None = None,
        include_children: bool = True
):
    return ResponseUnit(unit_id, name, date, price, parent_id, unit_type, children, include_children)


def generate_response_offer(
        unit_id: str = None,
        name: str = None,
        date: datetime.datetime | None = None,
        price: int | None = None,
        parent_id: str | None = None,
        include_children: bool = True
):
    return ResponseOffer(unit_id, name, date, price, parent_id, include_children)


def generate_response_category(
        unit_id: str = None,
        name: str = None,
        date: datetime.datetime | None = None,
        parent_id: str | None = None,
        children: list | None = None,
        include_children: bool = True
):
    return ResponseCategory(unit_id, name, date, parent_id, children, include_children)


def normalize_response_unit(unit: dict | ResponseUnit):
    if isinstance(unit, ResponseUnit):
        unit = unit.json()

    if 'children' in unit and unit['children'] is not None:
        unit['children'] = normalize_response_units(unit['children'])

    return unit


def compare_units(left: dict | ResponseUnit, right: dict | ResponseUnit):
    return normalize_response_unit(left) == normalize_response_unit(right)


def normalize_response_units(units: list[dict | ResponseUnit]) -> list:
    units = list(map(normalize_response_unit, units))

    return sorted(units, key=lambda x: (x['id'], x['date']))


def compare_unit_lists(left: list, right: list):
    return normalize_response_units(left) == normalize_response_units(right)
