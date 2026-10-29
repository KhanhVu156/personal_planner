"""Fix relationship transaction wallet

Revision ID: b94858a0ebd4
Revises: 330700a23963
Create Date: 2026-10-29 15:32:33.368371

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b94858a0ebd4'
down_revision = '330700a23963'
branch_labels = None
depends_on = None


def upgrade():
    # =================================================================
    # TƯ DUY SỬA LỖI (CRITICAL FIX):
    # 1. Lỗi "Constraint must have a name" xảy ra do Alembic tự sinh 
    #    lệnh drop_constraint(None) khi nó không tìm thấy tên FK.
    # 2. Trong SQLite/Turso, khi dùng batch_alter_table, Alembic sẽ tự
    #    động tạo bảng mới và copy dữ liệu sang. Việc gọi drop_constraint
    #    bằng tay là KHÔNG CẦN THIẾT và gây crash.
    # 3. Giải pháp: Xóa các dòng drop_constraint(None), đồng thời đặt 
    #    TÊN CỤ THỂ cho các create_foreign_key để sau này dễ quản lý.
    # =================================================================

    with op.batch_alter_table('budget', schema=None) as batch_op:
        # Đã xóa: batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_budget_user_id', 'user', ['user_id'], ['id'], ondelete='CASCADE'
        )

    with op.batch_alter_table('task', schema=None) as batch_op:
        # CẢNH BÁO: Nếu trong DB đang có dòng có giá trị NULL ở các cột này, 
        # việc set nullable=False sẽ gây lỗi "NOT NULL constraint failed".
        # Khuyên dùng: Chạy câu lệnh UPDATE để gán giá trị mặc định trước khi migrate.
        batch_op.alter_column('status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)
        batch_op.alter_column('progress',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('milestone',
               existing_type=sa.BOOLEAN(),
               nullable=False)
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=False)
        
        # Đã xóa: batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_task_user_id', 'user', ['user_id'], ['id'], ondelete='CASCADE'
        )

    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=False)
        batch_op.drop_index(batch_op.f('ix_trans_user_category_date'))
        batch_op.create_index('ix_trans_user_wallet_date', ['user_id', 'wallet_id', 'date'], unique=False)
        
        # Đã xóa: batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_transaction_user_id', 'user', ['user_id'], ['id'], ondelete='CASCADE'
        )

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=False)
        batch_op.create_index(batch_op.f('ix_user_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_user_username'), ['username'], unique=True)


def downgrade():
    # =================================================================
    # TƯ DUY DOWNGRADE:
    # Áp dụng nguyên tắc tương tự như upgrade. Xóa drop_constraint(None)
    # và thêm tên cho các constraint được khôi phục.
    # =================================================================

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_username'))
        batch_op.drop_index(batch_op.f('ix_user_email'))
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=True)

    with op.batch_alter_table('transaction', schema=None) as batch_op:
        # Đã xóa: batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_transaction_user_id', 'user', ['user_id'], ['id']
        )
        batch_op.drop_index('ix_trans_user_wallet_date')
        batch_op.create_index(batch_op.f('ix_trans_user_category_date'), ['user_id', 'category', 'date'], unique=False)
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=True)

    with op.batch_alter_table('task', schema=None) as batch_op:
        # Đã xóa: batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_task_user_id', 'user', ['user_id'], ['id']
        )
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=True)
        batch_op.alter_column('milestone',
               existing_type=sa.BOOLEAN(),
               nullable=True)
        batch_op.alter_column('progress',
               existing_type=sa.INTEGER(),
               nullable=True)
        batch_op.alter_column('status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)

    with op.batch_alter_table('budget', schema=None) as batch_op:
        # Đã xóa: batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_budget_user_id', 'user', ['user_id'], ['id']
        )