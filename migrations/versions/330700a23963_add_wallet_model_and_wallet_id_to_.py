"""Add Wallet model and wallet_id to Transaction

Revision ID: 330700a23963
Revises: 7a88bb90224e
Create Date: 2026-10-29 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '330700a23963'
down_revision = '7a88bb90224e'
branch_labels = None
depends_on = None


def upgrade():
    # ✅ Dọn dẹp bảng wallet cũ nếu có (do lần chạy trước bị lỗi giữa chừng)
    op.execute(text('DROP TABLE IF EXISTS wallet'))

    # 1. TẠO BẢNG WALLET
    op.create_table('wallet',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('wallet_type', sa.String(length=20), nullable=False),
        sa.Column('initial_balance', sa.Numeric(precision=30, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("wallet_type IN ('cash', 'bank', 'ewallet', 'credit')", name='ck_wallet_type'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_wallet_user_name')
    )
    with op.batch_alter_table('wallet', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_wallet_user_id'), ['user_id'], unique=False)

    # 2. THÊM CỘT WALLET_ID VÀO BẢNG TRANSACTION
    conn = op.get_bind()
    # ✅ FIX: "transaction" là từ khóa SQL, phải bọc trong dấu ngoặc kép ""
    res = conn.execute(text('PRAGMA table_info("transaction")'))
    columns = [row[1] for row in res.fetchall()]

    if 'wallet_id' not in columns:
        with op.batch_alter_table('transaction', schema=None) as batch_op:
            batch_op.add_column(sa.Column('wallet_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_transaction_wallet_id', 'wallet', ['wallet_id'], ['id'], ondelete='RESTRICT')
            batch_op.create_index(batch_op.f('ix_transaction_wallet_id'), ['wallet_id'], unique=False)


def downgrade():
    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_transaction_wallet_id'))
        batch_op.drop_constraint('fk_transaction_wallet_id', type_='foreignkey')
        batch_op.drop_column('wallet_id')

    with op.batch_alter_table('wallet', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_wallet_user_id'))
    op.drop_table('wallet')