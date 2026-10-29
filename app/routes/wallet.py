from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.forms import WalletForm 
from app.models import Wallet, Transaction
from sqlalchemy import func

bp = Blueprint('wallets', __name__)

@bp.route('/wallets')
@login_required
def list_wallets():
    # Đọc tham số show_hidden từ URL
    show_hidden = request.args.get('show_hidden', '0') == '1'

    # Nếu show_hidden = True -> Lấy TẤT CẢ ví. Ngược lại -> Chỉ lấy ví active.
    query = Wallet.query.filter_by(user_id=current_user.id)
    if not show_hidden:
        query = query.filter_by(is_active=True)
        
    # Ưu tiên ví active lên trước
    wallets = query.order_by(Wallet.is_active.desc(), Wallet.created_at.asc()).all()
    
    # Tính số dư
    flows = db.session.query(
        Transaction.wallet_id,
        Transaction.type,
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.wallet_id.isnot(None)
    ).group_by(Transaction.wallet_id, Transaction.type).all()

    flow_dict = {}
    for w_id, t_type, total in flows:
        if w_id not in flow_dict:
            flow_dict[w_id] = {'income': 0.0, 'expense': 0.0}
        flow_dict[w_id][t_type] = float(total)

    for w in wallets:
        in_flow = flow_dict.get(w.id, {}).get('income', 0.0)
        out_flow = flow_dict.get(w.id, {}).get('expense', 0.0)
        w.current_balance = float(w.initial_balance or 0) + in_flow - out_flow

    return render_template('wallet/list.html', wallets=wallets, show_hidden=show_hidden)

@bp.route('/wallets/add', methods=['GET', 'POST'])
@login_required
def add_wallet():
    form = WalletForm()
    if form.validate_on_submit():
        existing = Wallet.query.filter_by(user_id=current_user.id, name=form.name.data.strip()).first()
        if existing:
            flash('Tên ví này đã tồn tại. Vui lòng chọn tên khác.', 'warning')
            return render_template('wallet/form.html', form=form, title='Thêm Ví mới')

        try:
            wallet = Wallet(
                user_id=current_user.id,
                name=form.name.data.strip(),
                wallet_type=form.wallet_type.data,
                initial_balance=form.initial_balance.data or 0
            )
            db.session.add(wallet)
            db.session.commit()
            flash('Đã thêm ví mới thành công.', 'success')
            return redirect(url_for('wallets.list_wallets'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi thêm ví: {str(e)}")
            flash('Có lỗi xảy ra khi lưu ví. Vui lòng thử lại.', 'danger')

    return render_template('wallet/form.html', form=form, title='Thêm Ví mới')

@bp.route('/wallets/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_wallet(id):
    wallet = Wallet.query.get_or_404(id)
    if wallet.user_id != current_user.id or not wallet.is_active:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('wallets.list_wallets'))

    form = WalletForm(obj=wallet)
    
    if form.validate_on_submit():
        existing = Wallet.query.filter(
            Wallet.user_id == current_user.id,
            Wallet.name == form.name.data.strip(),
            Wallet.id != id,
            Wallet.is_active == True
        ).first()
        
        if existing:
            flash('Tên ví này đã tồn tại. Vui lòng chọn tên khác.', 'warning')
            return render_template('wallet/form.html', form=form, title='Sửa Ví')

        try:
            form.populate_obj(wallet)
            wallet.name = form.name.data.strip()
            db.session.commit()
            flash('Đã cập nhật thông tin ví.', 'success')
            return redirect(url_for('wallets.list_wallets'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi sửa ví ID {id}: {str(e)}")
            flash('Có lỗi xảy ra khi cập nhật ví. Vui lòng thử lại.', 'danger')

    return render_template('wallet/form.html', form=form, title='Sửa Ví')

@bp.route('/wallets/delete/<int:id>', methods=['POST'])
@login_required
def delete_wallet(id):
    wallet = Wallet.query.get_or_404(id)
    if wallet.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('wallets.list_wallets'))

    try:
        wallet.is_active = False
        db.session.commit()
        flash(f'Đã ẩn ví "{wallet.name}". Dữ liệu giao dịch cũ vẫn được giữ nguyên.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi ẩn ví ID {id}: {str(e)}")
        flash('Có lỗi xảy ra khi xóa ví. Vui lòng thử lại.', 'danger')

    return redirect(url_for('wallets.list_wallets', show_hidden=1 if request.args.get('show_hidden') else 0))

# ✅ THÊM ROUTE KHÔI PHỤC VÍ
@bp.route('/wallets/restore/<int:id>', methods=['POST'])
@login_required
def restore_wallet(id):
    wallet = Wallet.query.get_or_404(id)
    if wallet.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('wallets.list_wallets'))
        
    try:
        wallet.is_active = True
        db.session.commit()
        flash(f'Đã khôi phục ví "{wallet.name}".', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khôi phục ví ID {id}: {str(e)}")
        flash('Có lỗi xảy ra. Vui lòng thử lại.', 'danger')
        
    return redirect(url_for('wallets.list_wallets', show_hidden=1))