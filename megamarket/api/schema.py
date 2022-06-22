from datetime import datetime

from marshmallow import validates_schema, ValidationError
from marshmallow.fields import String, Integer, DateTime, Nested, List, Dict
from marshmallow.schema import Schema
from marshmallow.validate import OneOf, Range, Length

from megamarket.db.schema import ShopUnitType

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


class ShopUnitSchema(Schema):
    id = String(required=True, validate=Length(min=1))
    name = String(required=True, validate=Length(min=1, max=256))
    date = DateTime(required=True, format=DATETIME_FORMAT)
    type = String(required=True, validate=OneOf([unit_type.value for unit_type in ShopUnitType]))

    parentId = String(required=False, allow_none=True, validate=Length(min=1))
    price = Integer(required=False, allow_none=True, validate=Range(min=0))
    children = List(Nested(lambda: ShopUnitSchema()), required=False, allow_none=True)

    @validates_schema
    def validate_parent_is_not_self(self, data, **_):
        if data['parentId'] is not None and data['parentId'] == data['id']:
            raise ValidationError('Parent cannot be itself')

    @validates_schema
    def validate_date(self, data, **_):
        if 'date' in data:
            if data['date'] > datetime.now():
                raise ValidationError('Date cannot be in future')


class ShopUnitImportSchema(Schema):
    id = String(required=True, validate=Length(min=1))
    name = String(required=True, validate=Length(min=1, max=256))
    type = String(required=True, validate=OneOf([unit_type.value for unit_type in ShopUnitType]))

    parentId = String(required=False, allow_none=True, validate=Length(min=1))
    price = Integer(required=False, allow_none=True, validate=Range(min=0))

    @validates_schema
    def validate_category_price(self, data, **_):
        if data['type'] == ShopUnitType.CATEGORY.value and 'price' in data:
            if data['price'] is not None:
                raise ValidationError('Price is not allowed for categories')

    @validates_schema
    def validate_parent_is_not_self(self, data, **_):
        if data['parentId'] is not None and data['parentId'] == data['id']:
            raise ValidationError('Parent cannot be itself')

    @validates_schema
    def validate_offer_price(self, data, **_):
        if data['type'] == 'OFFER':
            if 'price' not in data or data['price'] is None:
                raise ValidationError('Offer should have a price')


class ShopUnitImportRequestSchema(Schema):
    items = List(Nested(ShopUnitImportSchema()), required=False)
    updateDate = DateTime(required=True, format=DATETIME_FORMAT)

    @validates_schema
    def validate_items(self, data, **_):
        items = set()
        for item in data['items']:
            if item['id'] in items:
                raise ValidationError('Duplicate item')
            items.add(item['id'])

    @validates_schema
    def validate_date(self, data, **_):
        if 'updateDate' in data:
            if data['updateDate'] > datetime.now():
                raise ValidationError('Date cannot be in future')


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
    price = Integer(required=False, allow_none=True, validate=Range(min=0))

    @validates_schema
    def validate_parent_is_not_self(self, data, **_):
        if data['parentId'] is not None and data['parentId'] == data['id']:
            raise ValidationError('Parent cannot be itself')

    @validates_schema
    def validate_date(self, data, **_):
        if 'date' in data:
            if data['date'] > datetime.now():
                raise ValidationError('Date cannot be in future')


class ShopUnitStatisticResponseSchema(Schema):
    items = List(Nested(ShopUnitStatisticUnitSchema()), required=False)


class ErrorResponseSchema(Schema):
    code = Integer(required=True)
    message = String(required=True, validate=Length(min=1))

    fields = Dict(required=False)
