"""location_filter added to exercise model

Revision ID: d7cda8d0f36f
Revises: 78fcdab91e71
Create Date: 2023-08-03 11:09:42.400844

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7cda8d0f36f'
down_revision = '78fcdab91e71'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('exercises', sa.Column('location_filter', sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('exercises', 'location_filter')
    # ### end Alembic commands ###
