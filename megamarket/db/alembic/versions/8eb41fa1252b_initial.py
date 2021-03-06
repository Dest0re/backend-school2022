"""Initial

Revision ID: 8eb41fa1252b
Revises:
Create Date: 2022-06-14 18:49:14.318138

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8eb41fa1252b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('shop_unit_ids',
                    sa.Column('id', sa.String(), nullable=False, default=True),
                    sa.PrimaryKeyConstraint('id', name=op.f('pk__shop_unit_ids'))
                    )

    op.create_table('shop_unit_revisions',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('date', sa.DateTime(), nullable=False),
                    sa.Column('shop_unit_id', sa.String(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('price', sa.Integer(), nullable=True),
                    sa.Column('type', sa.Enum('OFFER', 'CATEGORY', name='shop_unit_type'),
                              nullable=False),
                    sa.ForeignKeyConstraint(
                        ['shop_unit_id'], ['shop_unit_ids.id'],
                        name=op.f(
                            'fk__shop_unit_revisions__shop_unit_id__shop_unit_ids'),
                        onupdate='RESTRICT', ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id', name=op.f('pk__shop_unit_revisions')),
                    sa.UniqueConstraint('shop_unit_id', 'date',
                                        name='uq__shop_unit_revisions__shop_unit_id_date')
                    )

    op.create_table('relations',
                    sa.Column('child_revision_id', sa.Integer(), nullable=False),
                    sa.Column('parent_id', sa.String(), nullable=False),
                    sa.ForeignKeyConstraint(['child_revision_id'], ['shop_unit_revisions.id'],
                                            name=op.f(
                                                'fk__relations__child_revision_'
                                                'id__shop_unit_revisions'),
                                            onupdate='RESTRICT', ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['parent_id'], ['shop_unit_ids.id'],
                                            name=op.f('fk__relations__parent_id__shop_unit_ids'),
                                            onupdate='RESTRICT', ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('child_revision_id', name='pk__relations'),
                    sa.UniqueConstraint('child_revision_id', 'parent_id',
                                        name=op.f('uq__relations__child_revision_id_parent_id'))
                    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('relations')
    op.drop_table('shop_unit_revisions')
    op.drop_table('shop_unit_ids')
    # ### end Alembic commands ###

    custom_type = sa.Enum('OFFER', 'CATEGORY', name='shop_unit_type')
    custom_type.drop(op.get_bind(), checkfirst=False)
