from marshmallow import validates_schema, ValidationError
from marshmallow.schema import Schema
from marshmallow.fields import String, Integer, DateTime, Nested, List, Boolean, Dict
from marshmallow.validate import OneOf, Range, Length

from megamarket.db.schema import ShopUnitType


DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


class ShopUnitSchema(Schema):
    id = String(required=True, validate=Length(min=1))
    name = String(required=True, validate=Length(min=1, max=256))
    date = DateTime(required=True, format=DATETIME_FORMAT)
    type = String(required=True, validate=OneOf([unit_type.value for unit_type in ShopUnitType]))

    parentId = String(required=False, allow_none=True, validate=Length(min=1))
    price = Integer(required=False, validate=Range(min=0))
    children = List(Nested(lambda: ShopUnitSchema()), required=False)


class ShopUnitImportSchema(Schema):
    id = String(required=True, validate=Length(min=1))
    name = String(required=True, validate=Length(min=1, max=256))
    type = String(required=True, validate=OneOf([unit_type.value for unit_type in ShopUnitType]))

    parentId = String(required=False, allow_none=True, validate=Length(min=1))
    price = Integer(required=False, validate=Range(min=0), allow_none=True)

    @validates_schema
    def validate_category_price(self, data, **_):
        if data['type'] == ShopUnitType.CATEGORY.value and 'price' in data:
            if data['price'] is not None:
                raise ValidationError('Price is not allowed for categories')


class ShopUnitImportRequestSchema(Schema):
    items = List(Nested(ShopUnitImportSchema()), required=False)
    updateDate = DateTime(required=False, format=DATETIME_FORMAT)

    @validates_schema
    def validate_items(self, data, **_):
        items = set()
        for item in data['items']:
            if item['id'] in items:
                raise ValidationError('Duplicate item')
            items.add(item['id'])


class SalesRequestParamsSchema(Schema):
    date = DateTime(required=True, format=DATETIME_FORMAT)


class ShopUnitStatisticsRequestParamsSchema(Schema):
    dateStart = DateTime(required=False, format=DATETIME_FORMAT)
    dateEnd = DateTime(required=False, format=DATETIME_FORMAT)

    @validates_schema
    def validate_dates(self, data, **_):
        if 'dateStart' in data and 'dateEnd' in data:
            if data['dateStart'] >= data['dateEnd']:
                raise ValidationError('Date start must be less than date end')


class ShopUnitStatisticUnitSchema(Schema):
    id = String(required=True, validate=Length(min=1))
    name = String(required=True, validate=Length(min=1, max=256))
    type = String(required=True, validate=OneOf([unit_type.value for unit_type in ShopUnitType]))
    date = DateTime(required=True, format=DATETIME_FORMAT)

    parentId = String(required=False, allow_none=True, validate=Length(min=1))
    price = Integer(required=False, validate=Range(min=0), strict=True)


class ShopUnitStatisticResponseSchema(Schema):
    items = List(Nested(ShopUnitStatisticUnitSchema()), required=False)


class ErrorResponseSchema(Schema):
    code = Integer(required=True)
    message = String(required=True, validate=Length(min=1))

    fields = Dict(required=False)
