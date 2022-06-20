"""Add triggers

Revision ID: d04941b49bad
Revises: 8eb41fa1252b
Create Date: 2022-06-14 19:03:19.276102

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd04941b49bad'
down_revision = '8eb41fa1252b'
branch_labels = None
depends_on = None

CREATE_CHECK_RELATIONSHIP_TRIGGER = """
CREATE OR REPLACE FUNCTION f_check_relationship()
    RETURNS TRIGGER 
    LANGUAGE plpgsql AS
$func$
BEGIN
    IF 'OFFER' IN (
        SELECT type 
        FROM shop_unit_revisions
        WHERE shop_unit_id = NEW.parent_id
        ORDER BY date DESC
        LIMIT 1
    ) THEN
        RAISE EXCEPTION USING HINT = 'Offer cannot be a parent', ERRCODE = 'object_not_in_prerequisite_state';
    END IF;

    RETURN NEW;
END
$func$;


CREATE TRIGGER t_check_relationship
BEFORE INSERT ON relations
FOR EACH ROW
EXECUTE PROCEDURE f_check_relationship();
"""

DROP_CHECK_RELATIONSHIP_TRIGGER = """
DROP TRIGGER t_check_relationship ON relations;
DROP FUNCTION f_check_relationship();
"""


CREATE_DELETE_CHILDREN_TRIGGER = """
CREATE OR REPLACE FUNCTION f_delete_children()
    RETURNS TRIGGER
    LANGUAGE plpgsql AS
$func$
BEGIN
    WITH tmp AS (
        WITH actual_parent_ids AS (
            WITH actual_revision_dates AS (
                SELECT MAX(date) AS max_date, shop_unit_id AS child_id
                FROM 
                    relations
                    INNER JOIN shop_unit_revisions sur ON relations.child_revision_id = sur.id
                GROUP BY sur.shop_unit_id
            )
            SELECT shop_unit_revisions.shop_unit_id AS child_id, parent_id
            FROM 
                shop_unit_revisions
                INNER JOIN actual_revision_dates ard ON shop_unit_revisions.shop_unit_id = ard.child_id 
                    AND shop_unit_revisions.date = ard.max_date
                INNER JOIN relations ON relations.child_revision_id = shop_unit_revisions.id
        )
        SELECT child_id
        FROM actual_parent_ids
        WHERE parent_id = OLD.id
    )
    DELETE FROM shop_unit_ids WHERE id IN (SELECT child_id FROM tmp);
    
    RETURN OLD;

END
$func$;

CREATE TRIGGER t_delete_children
BEFORE DELETE ON shop_unit_ids
FOR EACH ROW
EXECUTE PROCEDURE f_delete_children();
"""


DROP_DELETE_CHILDREN_TRIGGER = """
DROP TRIGGER t_delete_children ON shop_unit_ids;
DROP FUNCTION f_delete_children();
"""


CREATE_CHECK_UNIT_TYPE_CHANGE_TRIGGER = """
CREATE OR REPLACE FUNCTION f_check_unit_type_change()
    RETURNS TRIGGER
    LANGUAGE plpgsql AS
$func$
BEGIN
    IF EXISTS((
        SELECT type
        FROM shop_unit_revisions
        WHERE shop_unit_id = NEW.shop_unit_id
        ORDER BY date DESC
    ))
    THEN
        IF NEW.type NOT IN (
            SELECT type
            FROM shop_unit_revisions
            WHERE shop_unit_id = NEW.shop_unit_id
            ORDER BY date DESC
            LIMIT 1
        ) THEN
            RAISE EXCEPTION 'Unit type cannot be changed';
        END IF;
    END IF;
    
    RETURN NEW;
END
$func$;


CREATE TRIGGER t_check_unit_type_change
BEFORE INSERT ON shop_unit_revisions
FOR EACH ROW
EXECUTE PROCEDURE f_check_unit_type_change();
"""

DROP_CHECK_UNIT_TYPE_CHANGE_TRIGGER = """
DROP TRIGGER t_check_unit_type_change ON shop_unit_revisions;
DROP FUNCTION f_check_unit_type_change();
"""


def upgrade():
    op.execute(CREATE_CHECK_RELATIONSHIP_TRIGGER)
    op.execute(CREATE_CHECK_UNIT_TYPE_CHANGE_TRIGGER)
    op.execute(CREATE_DELETE_CHILDREN_TRIGGER)


def downgrade():
    op.execute(DROP_CHECK_RELATIONSHIP_TRIGGER)
    op.execute(DROP_CHECK_UNIT_TYPE_CHANGE_TRIGGER)
    op.execute(DROP_DELETE_CHILDREN_TRIGGER)
