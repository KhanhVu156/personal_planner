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
    """
    Hiển thị danh sách giao dịch có phân trang.
    Sử dụng server-side pagination để tránh tải toàn bộ dữ liệu vào RAM nếu user có hàng nghìn giao dịch.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 20 # Số lượng bản ghi mỗi trang
    
    # Sắp xếp giảm dần theo ngày để giao dịch mới nhất hiện lên đầu
    pagination = Transaction.query.filter_by(user_id=current_user.id) \
        .order_by(Transaction.date.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)
        
    return render_template('transactions/list.html', transactions=pagination)


@bp.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """
    Thêm giao dịch mới.
    Sử dụng Flask-WTF Form để tự động validate dữ liệu đầu vào (chống XSS, SQL Injection, ép kiểu tiền tệ).
    """
    form = TransactionForm()
    if form.validate_on_submit():
        try:
            # Tạo instance và gán dữ liệu từ form
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
        except Exception as e:
            # Tư duy: Luôn rollback nếu commit thất bại để giải phóng connection pool
            db.session.rollback()
            current_app.logger.error(f"Lỗi thêm giao dịch: {str(e)}")
            flash('Có lỗi xảy ra khi lưu giao dịch. Vui lòng thử lại.', 'danger')
            
    # Debug form errors ra log (chỉ hiển thị ở server, không lộ ra client)
    if form.errors:
        current_app.logger.warning(f"Form giao dịch lỗi: {form.errors}")
        
    return render_template('transactions/form.html', form=form, title='Thêm Giao dịch')


@bp.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    """
    Chỉnh sửa giao dịch.
    Tư duy: Phải kiểm tra quyền sở hữu (IDOR) - Ngăn chặn User A sửa giao dịch của User B thông qua việc đoán ID trên URL.
    """
    trans = Transaction.query.get_or_404(id)
    if trans.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('transactions.list_transactions'))
        
    # Khởi tạo form với dữ liệu cũ (obj=trans)
    form = TransactionForm(obj=trans)
    if form.validate_on_submit():
        try:
            form.populate_obj(trans) # Ghi đè dữ liệu mới từ form vào object cũ
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
    
    TƯ DUY THIẾT KẾ (CRITICAL FIX):
    - Sử dụng phương thức POST thay vì GET. Theo chuẩn HTTP, GET là Safe Method (chỉ đọc). 
      Nếu dùng GET để xóa, bot crawl web hoặc trình duyệt prefetch link có thể xóa sạch dữ liệu của user.
    - Phương thức POST yêu cầu phải có CSRF Token (đã được chèn ở form HTML) để chống tấn công Cross-Site Request Forgery.
    """
    trans = Transaction.query.get_or_404(id)
    
    # 1. Kiểm tra quyền sở hữu (Data Ownership) - Tránh lỗ hổng IDOR
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
    
    GIẢI THUẬT XỬ LÝ FILE:
    1. Đọc file dưới dạng bytes, kiểm tra BOM (Byte Order Mark) để nhận diện UTF-16.
    2. Fallback: Thử decode UTF-8 -> CP1258 (Tiếng Việt Windows) -> Latin-1 (chống crash file rác).
    3. Dùng csv.Sniffer() để tự động đoán dấu phân cách (phẩy, chấm phẩy).
    4. Làm sạch tên cột (chỉ giữ chữ cái) để tránh lỗi font từ Excel.
    5. Dùng batch processing (chia lô 500 bản ghi) để tránh tràn RAM (Out of Memory).
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
        
        # Xử lý Encoding đa tầng
        if isinstance(file_content, bytes):
            if file_content.startswith(b'\xff\xfe') or file_content.startswith(b'\xfe\xff'):
                file_content = file_content.decode('utf-16')
            else:
                try:
                    file_content = file_content.decode('utf-8-sig') # Xử lý BOM của Excel
                except UnicodeDecodeError:
                    try:
                        file_content = file_content.decode('cp1258') # Chuẩn tiếng Việt
                    except UnicodeDecodeError:
                        file_content = file_content.decode('latin-1', errors='replace') # Cứu cánh cuối cùng
        
        file_content = file_content.replace('\x00', '') # Xóa ký tự null ẩn
        stream = io.StringIO(file_content, newline='')
        
        # Tự động nhận diện delimiter (, hoặc ;)
        try:
            dialect = csv.Sniffer().sniff(stream.read(1024))
            stream.seek(0)
        except csv.Error:
            dialect = 'excel' # Mặc định dùng dấu phẩy

        csv_input = csv.DictReader(stream, dialect=dialect)
        
        # Chuẩn hóa tên cột (VD: "Số Tiền " -> "sotien")
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

        count = 0
        batch = []
        
        for row in csv_input:
            try:
                date_str = row.get('date', '').strip()
                amount_str = row.get('amount', '').strip()
                
                # Dùng Regex để trích xuất ngày chuẩn YYYY-MM-DD (bất chấp định dạng Excel)
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
                if date_match:
                    date = datetime.strptime(date_match.group(), '%Y-%m-%d').date()
                else:
                    continue # Bỏ qua dòng lỗi ngày tháng

                # Trích xuất số tiền
                amount_match = re.search(r'\d+(\.\d+)?', amount_str)
                if amount_match:
                    amount = float(amount_match.group())
                else:
                    continue # Bỏ qua dòng lỗi số tiền
                    
            except Exception:
                continue # Bỏ qua dòng dữ liệu rác, không làm sập toàn bộ quá trình import
                
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
            
            # Bulk insert từng lô 500 bản ghi để giải phóng bộ nhớ
            if len(batch) >= 500:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []
                
        # Lưu lô cuối cùng còn sót lại
        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()
            
        flash(f'Đã nhập thành công {count} giao dịch.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi Import CSV: {str(e)}")
        flash(f'Lỗi xử lý file: {str(e)}', 'danger')

    return redirect(url_for('transactions.list_transactions'))