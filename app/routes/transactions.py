from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.forms import TransactionForm
from app.models import Transaction
from datetime import datetime
import csv
import io

bp = Blueprint('transactions', __name__)

@bp.route('/transactions')
@login_required
def list_transactions():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = Transaction.query.filter_by(user_id=current_user.id) \
        .order_by(Transaction.date.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('transactions/list.html', transactions=pagination)

@bp.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    if form.validate_on_submit():
        trans = Transaction(
            user_id=current_user.id,
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
    return render_template('transactions/form.html', form=form, title='Thêm Giao dịch')

@bp.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    trans = Transaction.query.get_or_404(id)
    if trans.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('transactions.list_transactions'))
    form = TransactionForm(obj=trans)
    if form.validate_on_submit():
        form.populate_obj(trans)
        db.session.commit()
        flash('Đã cập nhật giao dịch.', 'success')
        return redirect(url_for('transactions.list_transactions'))
    return render_template('transactions/form.html', form=form, title='Sửa Giao dịch')

@bp.route('/transactions/delete/<int:id>')
@login_required
def delete_transaction(id):
    trans = Transaction.query.get_or_404(id)
    if trans.user_id == current_user.id:
        db.session.delete(trans)
        db.session.commit()
        flash('Đã xóa giao dịch.', 'success')
    else:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
    return redirect(url_for('transactions.list_transactions'))

@bp.route('/transactions/import', methods=['POST'])
@login_required
def import_csv():
    if 'csv_file' not in request.files:
        flash('Chưa có file nào được tải lên.', 'danger')
        return redirect(url_for('transactions.list_transactions'))
    file = request.files['csv_file']
    if file.filename == '':
        flash('File rỗng.', 'danger')
        return redirect(url_for('transactions.list_transactions'))

    try:
        # SỬ DỤNG GENERATOR: Đọc từng dòng, không load toàn bộ file vào RAM
        stream = io.TextIOWrapper(file.stream, encoding='utf-8')
        csv_input = csv.DictReader(stream)
        
        required_fields = {'date', 'description', 'amount', 'category', 'type'}
        if not required_fields.issubset(set(csv_input.fieldnames or [])):
            flash('File CSV phải chứa các cột: date, description, amount, category, type.', 'danger')
            return redirect(url_for('transactions.list_transactions'))

        count = 0
        batch = []
        
        for row in csv_input:
            try:
                date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                amount = float(row['amount'])
            except Exception:
                continue 
                
            trans = Transaction(
                user_id=current_user.id,
                date=date,
                description=row['description'],
                amount=amount,
                category=row['category'],
                type=row['type']
            )
            batch.append(trans)
            count += 1
            
            # BULK INSERT: Cứ 500 dòng thì ghi 1 lần để giải phóng RAM
            if len(batch) >= 500:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []
                
        # Ghi nốt những dòng còn sót lại
        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()
            
        flash(f'Đã nhập thành công {count} giao dịch.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi Import CSV: {str(e)}")
        flash(f'Lỗi xử lý file: {str(e)}', 'danger')

    return redirect(url_for('transactions.list_transactions'))