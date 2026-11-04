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
    """
    Hiển thị danh sách các Ví.
    TƯ DUY: Tách biệt hoàn toàn 2 danh sách: Ví đang hoạt động và Ví đã ẩn dựa vào tabs.
    """
    # Đọc tham số show_hidden từ URL (Mặc định là False - Tab Ví đang hoạt động)
    show_hidden = request.args.get('show_hidden', '0') == '1'

    query = Wallet.query.filter_by(user_id=current_user.id)
    
    # ✅ TÁCH BIỆT LOGIC QUERY CHO 2 TAB
    if show_hidden:
        query = query.filter_by(is_active=False) # Tab 2: Chỉ lấy ví đã ẩn
    else:
        query = query.filter_by(is_active=True)  # Tab 1: Chỉ lấy ví đang hoạt động
        
    # Sắp xếp theo ngày tạo (mới nhất lên đầu)
    wallets = query.order_by(Wallet.created_at.desc()).all()
    
    # =====================================================================
    # TƯ DUY TỐI ƯU TRUY VẤN (CHỐNG N+1 QUERY):
    # Thay vì loop qua từng ví và query DB (gây chậm), ta dùng 1 câu query 
    # GROUP BY để tính tổng thu/chi của TẤT CẢ các ví cùng lúc.
    # =====================================================================
    flows = db.session.query(
        Transaction.wallet_id,
        Transaction.type,
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.wallet_id.isnot(None)
    ).group_by(Transaction.wallet_id, Transaction.type).all()

    # Map flow (luồng thu/chi) vào dictionary để tra cứu O(1)
    flow_dict = {}
    for w_id, t_type, total in flows:
        if w_id not in flow_dict:
            flow_dict[w_id] = {'income': 0.0, 'expense': 0.0}
        # Ép kiểu float an toàn để tránh lỗi Decimal từ DB
        flow_dict[w_id][t_type] = float(total or 0)

    # Tính toán số dư hiện tại và gán trực tiếp vào object để Template hiển thị
    for w in wallets:
        in_flow = flow_dict.get(w.id, {}).get('income', 0.0)
        out_flow = flow_dict.get(w.id, {}).get('expense', 0.0)
        w.current_balance = float(w.initial_balance or 0) + in_flow - out_flow

    return render_template('wallet/list.html', wallets=wallets, show_hidden=show_hidden)


@bp.route('/wallets/add', methods=['GET', 'POST'])
@login_required
def add_wallet():
    """
    Thêm ví mới.
    """
    form = WalletForm()
    if form.validate_on_submit():
        wallet_name = form.name.data.strip()
        
        existing = Wallet.query.filter_by(user_id=current_user.id, name=wallet_name).first()
        if existing:
            flash('Tên ví này đã tồn tại. Vui lòng chọn tên khác.', 'warning')
            return render_template('wallet/form.html', form=form, title='Thêm Ví mới')

        try:
            wallet = Wallet(
                user_id=current_user.id,
                name=wallet_name,
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
    """
    Chỉnh sửa thông tin ví.
    TƯ DUY: Chỉ cho phép sửa các ví đang hoạt động.
    """
    wallet = Wallet.query.get_or_404(id)
    if wallet.user_id != current_user.id or not wallet.is_active:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('wallets.list_wallets'))

    form = WalletForm(obj=wallet)
    
    if form.validate_on_submit():
        wallet_name = form.name.data.strip()
        
        existing = Wallet.query.filter(
            Wallet.user_id == current_user.id,
            Wallet.name == wallet_name,
            Wallet.id != id,
            Wallet.is_active == True
        ).first()
        
        if existing:
            flash('Tên ví này đã tồn tại. Vui lòng chọn tên khác.', 'warning')
            return render_template('wallet/form.html', form=form, title='Sửa Ví')

        try:
            form.populate_obj(wallet)
            wallet.name = wallet_name
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
    """
    Xóa (Ẩn) ví.
    TƯ DUY XÓA MỀM (Soft Delete): Không xóa cứng khỏi DB để bảo toàn lịch sử giao dịch.
    """
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

    # Giữ nguyên trạng thái tab hiện tại (thường là tab 1)
    show_hidden = request.form.get('show_hidden', '0')
    return redirect(url_for('wallets.list_wallets', show_hidden=show_hidden))


@bp.route('/wallets/delete-permanent/<int:id>', methods=['POST'])
@login_required
def delete_wallet_permanent(id):
    """
    Xóa VĨNH VIỄN ví (Hard Delete).
    TƯ DUY XỬ LÝ RÀNG BUỘC DỮ LIỆU (DATABASE INTEGRITY):
    - Xóa toàn bộ Giao dịch liên quan trước khi xóa Ví để tránh lỗi Khóa Ngoại.
    """
    wallet = Wallet.query.get_or_404(id)
    if wallet.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('wallets.list_wallets'))

    try:
        Transaction.query.filter_by(wallet_id=wallet.id).delete()
        db.session.delete(wallet)
        db.session.commit()
        flash(f'Đã xóa vĩnh viễn ví "{wallet.name}" và các giao dịch liên quan.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi xóa vĩnh viễn ví ID {id}: {str(e)}")
        flash('Có lỗi xảy ra khi xóa vĩnh viễn ví. Vui lòng thử lại.', 'danger')

    show_hidden = request.form.get('show_hidden', '0')
    return redirect(url_for('wallets.list_wallets', show_hidden=show_hidden))


@bp.route('/wallets/restore/<int:id>', methods=['POST'])
@login_required
def restore_wallet(id):
    """
    Khôi phục ví đã ẩn.
    """
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
        
    # Giữ nguyên trạng thái tab hiện tại (thường là tab 2)
    show_hidden = request.form.get('show_hidden', '0')
    return redirect(url_for('wallets.list_wallets', show_hidden=show_hidden))