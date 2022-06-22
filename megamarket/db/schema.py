from enum import Enum, unique

from sqlalchemy import (
    Column, Table, MetaData, Integer, String, ForeignKey, Enum as PgEnum, DateTime,
    PrimaryKeyConstraint,
    UniqueConstraint
)

convention = {
    'all_column_names': lambda constraint, table: '_'.join([
        column.name for column in constraint.columns.values()
    ]),
    'ix': 'ix__%(table_name)s__%(all_column_names)s',
    'uq': 'uq__%(table_name)s__%(all_column_names)s',
    'ck': 'ck__%(table_name)s__%(constraint_name)s',
    'fk': 'fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s',
    'pk': 'pk__%(table_name)s'
}

metadata = MetaData(naming_convention=convention)


@unique
class ShopUnitType(Enum):
    OFFER = 'OFFER'
    CATEGORY = 'CATEGORY'


shop_unit_ids_table = Table(
    'shop_unit_ids', metadata,
    Column('id', String, primary_key=True),
)

shop_unit_revisions_table = Table(
    'shop_unit_revisions', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('date', DateTime, nullable=False),
    Column('shop_unit_id', String,
           ForeignKey('shop_unit_ids.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False),
    Column('name', String, nullable=False),
    Column('price', Integer, nullable=True),
    Column('type', PgEnum(ShopUnitType, name='shop_unit_type'), nullable=False),
    UniqueConstraint('shop_unit_id', 'date', name='uq__shop_unit_revisions__shop_unit_id_date'),
)

relations_table = Table(
    'relations', metadata,
    Column('child_revision_id', Integer,
           ForeignKey('shop_unit_revisions.id', ondelete='CASCADE', onupdate='RESTRICT'),
           nullable=False),
    Column('parent_id', String,
           ForeignKey('shop_unit_ids.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False),
    UniqueConstraint('child_revision_id', 'parent_id'),
    PrimaryKeyConstraint('child_revision_id', name='pk__relations'),
)
