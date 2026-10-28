from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.forms import TransactionForm
from app.models import Transaction
from datetime import datetime
import csv
import io
import re

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
    
    # ✅ In lỗi ra Terminal để dễ debug
    if form.errors:
        print("LỖI FORM GIAO DỊCH:", form.errors)
        
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
        
    # ✅ In lỗi ra Terminal
    if form.errors:
        print("LỖI FORM GIAO DỊCH:", form.errors)
        
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
            flash(f'File CSV thiếu cột. Các cột tìm thấy: {", ".join(csv_input.fieldnames)}. Yêu cầu: date, description, amount, category, type.', 'danger')
            return redirect(url_for('transactions.list_transactions'))

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