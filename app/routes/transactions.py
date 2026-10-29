from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.forms import TransactionForm
from app.models import Transaction, Wallet
from datetime import datetime
import csv
import io
import re
from sqlalchemy.orm import joinedload

bp = Blueprint('transactions', __name__)


def _populate_wallet_choices(form):
    """
    Helper: Nạp danh sách ví đang hoạt động của user vào form.
    TƯ DUY: Dịch các loại ví (cash, bank,...) sang tiếng Việt để đồng bộ với trang Quản lý Ví.
    """
    wallets = current_user.wallets.filter_by(is_active=True).order_by(Wallet.name).all()
    
    # 1. Từ điển map loại ví sang tiếng Việt
    type_names = {
        'cash': 'Tiền mặt',
        'bank': 'Ngân hàng',
        'ewallet': 'Ví điện tử',
        'credit': 'Thẻ tín dụng'
    }
    
    # 2. Khởi tạo danh sách với tùy chọn "Không chọn ví" mặc định
    choices = [(0, '-- Không chọn ví --')]
    
    # 3. Thêm các ví đang hoạt động vào danh sách với tên loại đã dịch
    for w in wallets:
        # Lấy tên tiếng Việt, nếu không có trong từ điển thì giữ nguyên giá trị gốc
        type_label = type_names.get(w.wallet_type, w.wallet_type) 
        choices.append((w.id, f"{w.name} ({type_label})"))
    
    form.wallet_id.choices = choices


@bp.route('/transactions')
@login_required
def list_transactions():
    """
    Hiển thị danh sách giao dịch có phân trang.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20 
    
    # Tối ưu: Eager load wallet để tránh N+1 query
    pagination = Transaction.query.filter_by(user_id=current_user.id) \
        .options(joinedload(Transaction.wallet)) \
        .order_by(Transaction.date.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)
        
    return render_template('transactions/list.html', transactions=pagination)


@bp.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """
    Thêm giao dịch mới.
    """
    form = TransactionForm()
    
    # Nạp danh sách ví TRƯỚC KHI validate
    _populate_wallet_choices(form)

    if form.validate_on_submit():
        try:
            # Xử lý wallet_id: 0 thành None
            wallet_id_val = form.wallet_id.data
            if wallet_id_val == 0:
                wallet_id_val = None

            trans = Transaction(
                user_id=current_user.id,
                wallet_id=wallet_id_val,
                date=form.date.data,
                description=form.description.data,
                amount=form.amount.data,
                category=form.category.data,
                type=form.type.data
            )
            db.session.add(trans)
            db.session.commit()
            flash('Đã thêm giao dịch thành công.', 'success')
            return redirect(url_for('transactions.list_transactions'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi thêm giao dịch: {str(e)}")
            flash('Có lỗi xảy ra khi lưu giao dịch. Vui lòng thử lại.', 'danger')
            
    if form.errors:
        current_app.logger.warning(f"Form giao dịch lỗi: {form.errors}")
        
    return render_template('transactions/form.html', form=form, title='Thêm Giao dịch')


@bp.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    """
    Chỉnh sửa giao dịch.
    """
    trans = Transaction.query.get_or_404(id)
    if trans.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('transactions.list_transactions'))
        
    form = TransactionForm(obj=trans)
    
    _populate_wallet_choices(form)

    if form.validate_on_submit():
        try:
            trans.date = form.date.data
            trans.description = form.description.data
            trans.amount = form.amount.data
            trans.category = form.category.data
            trans.type = form.type.data
            
            # Xử lý wallet_id tương tự hàm Add
            wallet_id_val = form.wallet_id.data
            trans.wallet_id = None if wallet_id_val == 0 else wallet_id_val

            db.session.commit()
            flash('Đã cập nhật giao dịch.', 'success')
            return redirect(url_for('transactions.list_transactions'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi sửa giao dịch ID {id}: {str(e)}")
            flash('Có lỗi xảy ra khi cập nhật. Vui lòng thử lại.', 'danger')
            
    if form.errors:
        current_app.logger.warning(f"Form sửa giao dịch lỗi: {form.errors}")
        
    return render_template('transactions/form.html', form=form, title='Sửa Giao dịch')


@bp.route('/transactions/delete/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    """
    Xử lý yêu cầu xóa giao dịch.
    """
    trans = Transaction.query.get_or_404(id)
    
    if trans.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('transactions.list_transactions'))
        
    try:
        db.session.delete(trans)
        db.session.commit()
        flash('Đã xóa giao dịch.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi xóa giao dịch ID {id}: {str(e)}")
        flash('Có lỗi xảy ra khi xóa. Vui lòng thử lại sau.', 'danger')
        
    return redirect(url_for('transactions.list_transactions'))


@bp.route('/transactions/import', methods=['POST'])
@login_required
def import_csv():
    """
    Import giao dịch từ file CSV.
    """
    if 'csv_file' not in request.files:
        flash('Chưa có file nào được tải lên.', 'danger')
        return redirect(url_for('transactions.list_transactions'))
        
    file = request.files['csv_file']
    if file.filename == '':
        flash('File rỗng.', 'danger')
        return redirect(url_for('transactions.list_transactions'))

    try:
        file_content = file.read()
        
        if isinstance(file_content, bytes):
            if file_content.startswith(b'\xff\xfe') or file_content.startswith(b'\xfe\xff'):
                file_content = file_content.decode('utf-16')
            else:
                try:
                    file_content = file_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    try:
                        file_content = file_content.decode('cp1258')
                    except UnicodeDecodeError:
                        file_content = file_content.decode('latin-1', errors='replace')
        
        file_content = file_content.replace('\x00', '')
        stream = io.StringIO(file_content, newline='')
        
        try:
            dialect = csv.Sniffer().sniff(stream.read(1024))
            stream.seek(0)
        except csv.Error:
            dialect = 'excel'

        csv_input = csv.DictReader(stream, dialect=dialect)
        
        if csv_input.fieldnames:
            cleaned_fieldnames = []
            for f in csv_input.fieldnames:
                clean_name = re.sub(r'[^a-zA-Z]', '', str(f)).lower()
                cleaned_fieldnames.append(clean_name)
            csv_input.fieldnames = cleaned_fieldnames
        else:
            flash('File CSV trống hoặc không có dòng tiêu đề.', 'danger')
            return redirect(url_for('transactions.list_transactions'))

        required_fields = {'date', 'description', 'amount', 'category', 'type'}
        if not required_fields.issubset(set(csv_input.fieldnames)):
            flash(f'File CSV thiếu cột. Yêu cầu: date, description, amount, category, type.', 'danger')
            return redirect(url_for('transactions.list_transactions'))

        default_wallet = current_user.wallets.filter_by(is_active=True).order_by(Wallet.id).first()
        default_wallet_id = default_wallet.id if default_wallet else None

        count = 0
        batch = []
        
        for row in csv_input:
            try:
                date_str = row.get('date', '').strip()
                amount_str = row.get('amount', '').strip()
                
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
                if date_match:
                    date = datetime.strptime(date_match.group(), '%Y-%m-%d').date()
                else:
                    continue

                amount_match = re.search(r'\d+(\.\d+)?', amount_str)
                if amount_match:
                    amount = float(amount_match.group())
                else:
                    continue
                    
            except Exception:
                continue
                
            trans = Transaction(
                user_id=current_user.id,
                wallet_id=default_wallet_id,
                date=date,
                description=row.get('description', '').strip(),
                amount=amount,
                category=row.get('category', 'other').strip(),
                type=row.get('type', 'expense').strip()
            )
            batch.append(trans)
            count += 1
            
            if len(batch) >= 500:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []
                
        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()
            
        flash(f'Đã nhập thành công {count} giao dịch.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi Import CSV: {str(e)}")
        flash(f'Lỗi xử lý file: {str(e)}', 'danger')

    return redirect(url_for('transactions.list_transactions'))