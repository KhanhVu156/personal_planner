from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file
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


@bp.route('/transactions/download_template')
@login_required
def download_template():
    """
    Tạo và trả về file CSV mẫu.
    TƯ DUY FIX LỖI EXCEL: 
    Sử dụng cú pháp ="YYYY-MM-DD" cho cột Ngày để ép Excel hiểu đây là chuỗi Text.
    Điều này ngăn chặn việc Excel tự động format ngày và hiển thị lỗi ##### do cột quá hẹp.
    """
    csv_content = (
        "\ufeffNgày,Mô tả,Số tiền,Danh mục,Loại\r\n"
        '="2024-05-20",Ăn sáng,50000,food,expense\r\n'
        '="2024-05-21",Lương tháng 5,15000000,salary,income\r\n'
    )
    
    buffer = io.BytesIO()
    buffer.write(csv_content.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name='template_giao_dich.csv'
    )


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
    
    TƯ DUY GIẢI THUẬT XỬ LÝ FILE CSV ĐA NGÔN NGỮ:
    1. Đọc file: Ưu tiên utf-8-sig để tự động xóa ký tự BOM (\ufeff) thường gặp ở file Excel. Có fallback cho các bảng mã cũ.
    2. Đọc Header: Dùng csv.Sniffer() để tự động nhận diện dấu phân cách (phẩy, chấm phẩy).
    3. Chuẩn hóa Header: Xây dựng từ điển ánh xạ từ tiếng Việt (có dấu/không dấu) sang chuẩn tiếng Anh nội bộ.
    4. Xử lý Row (Dòng dữ liệu): 
       - Ngày: Dùng Regex tìm định dạng YYYY-MM-DD.
       - Số tiền: Làm sạch dấu phẩy/chấm phân cách (VD: "40,000" -> "40000") trước khi ép kiểu float.
       - Danh mục & Loại: Ánh xạ từ tiếng Việt sang tiếng Anh chuẩn để đồng bộ với Database và Dashboard.
    5. Lưu trữ: Dùng bulk_save_objects để tối ưu hiệu suất (chèn theo lô 500 dòng) thay vì commit từng dòng.
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
        
        # Bước 1: Xử lý Encoding (Mã hóa file)
        if isinstance(file_content, bytes):
            if file_content.startswith(b'\xff\xfe') or file_content.startswith(b'\xfe\xff'):
                file_content = file_content.decode('utf-16')
            else:
                try:
                    # utf-8-sig giúp tự động loại bỏ ký tự BOM (thường có ở file xuất từ Excel)
                    file_content = file_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    try:
                        file_content = file_content.decode('cp1258') # Tiếng Việt cũ
                    except UnicodeDecodeError:
                        file_content = file_content.decode('latin-1', errors='replace')
        
        file_content = file_content.replace('\x00', '')
        stream = io.StringIO(file_content, newline='')
        
        # Bước 2: Nhận diện dấu phân cách của file CSV (phẩy, chấm phẩy, tab...)
        try:
            dialect = csv.Sniffer().sniff(stream.read(1024))
            stream.seek(0)
        except csv.Error:
            dialect = 'excel' # Mặc định nếu không nhận diện được

        csv_input = csv.DictReader(stream, dialect=dialect)
        
        # Bước 3: Chuẩn hóa Header & Ánh xạ Tiếng Việt -> Tiếng Anh
        if not csv_input.fieldnames:
            flash('File CSV trống hoặc không có dòng tiêu đề.', 'danger')
            return redirect(url_for('transactions.list_transactions'))

        column_mapping = {
            'ngày': 'date', 'ngay': 'date', 'date': 'date',
            'mô tả': 'description', 'mo ta': 'description', 'description': 'description',
            'số tiền': 'amount', 'so tien': 'amount', 'amount': 'amount',
            'danh mục': 'category', 'danh muc': 'category', 'category': 'category',
            'loại': 'type', 'loai': 'type', 'type': 'type'
        }
        
        normalized_fieldnames = []
        for f in csv_input.fieldnames:
            clean_name = str(f).replace('\ufeff', '').strip().lower()
            mapped_name = column_mapping.get(clean_name, clean_name)
            normalized_fieldnames.append(mapped_name)
            
        csv_input.fieldnames = normalized_fieldnames

        # Kiểm tra các cột bắt buộc
        required_fields = {'date', 'description', 'amount', 'category', 'type'}
        if not required_fields.issubset(set(csv_input.fieldnames)):
            missing = required_fields - set(csv_input.fieldnames)
            
            field_vn_names = {
                'date': 'Ngày',
                'description': 'Mô tả',
                'amount': 'Số tiền',
                'category': 'Danh mục',
                'type': 'Loại'
            }
            missing_vn = [field_vn_names.get(f, f) for f in missing]
            
            flash(f'File CSV thiếu các cột bắt buộc: {", ".join(missing_vn)}. Vui lòng tải file mẫu để xem lại cấu trúc.', 'danger')
            return redirect(url_for('transactions.list_transactions'))

        # TƯ DUY FIX LỖI MAP TIẾNG VIỆT:
        # Xây dựng từ điển ánh xạ cả tiếng Việt (có dấu, không dấu) và tiếng Anh về chuẩn nội bộ.
        # Giúp người dùng không cần biết tiếng Anh vẫn có thể import file chính xác.
        category_map = {
            'ăn uống': 'food', 'an uong': 'food', 'food': 'food',
            'di chuyển': 'transport', 'di chuyen': 'transport', 'transport': 'transport',
            'học tập': 'education', 'hoc tap': 'education', 'education': 'education',
            'giải trí': 'entertainment', 'giai tri': 'entertainment', 'entertainment': 'entertainment',
            'mua sắm': 'shopping', 'mua sam': 'shopping', 'shopping': 'shopping',
            'hóa đơn': 'bills', 'hoa don': 'bills', 'bills': 'bills',
            'lương': 'salary', 'luong': 'salary', 'salary': 'salary',
            'khác': 'other', 'khac': 'other', 'other': 'other'
        }
        
        type_map = {
            'chi tiêu': 'expense', 'chi tieu': 'expense', 'chi': 'expense', 'expense': 'expense',
            'thu nhập': 'income', 'thu nhap': 'income', 'thu': 'income', 'income': 'income'
        }

        default_wallet = current_user.wallets.filter_by(is_active=True).order_by(Wallet.id).first()
        default_wallet_id = default_wallet.id if default_wallet else None

        count_success = 0
        count_error = 0
        batch = []
        
        # Bước 4 & 5: Đọc từng dòng, xử lý dữ liệu và lưu theo lô
        for row in csv_input:
            try:
                date_str = row.get('date', '').strip()
                amount_str = row.get('amount', '').strip()
                desc_str = row.get('description', '').strip()
                
                # 4.1. Xử lý Ngày tháng
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
                if not date_match:
                    count_error += 1
                    continue 
                date_obj = datetime.strptime(date_match.group(), '%Y-%m-%d').date()

                # 4.2. Xử lý Số tiền
                clean_amount_str = amount_str.replace(',', '').replace('.', '')
                amount_match = re.search(r'\d+', clean_amount_str)
                if not amount_match:
                    count_error += 1
                    continue
                amount_val = float(amount_match.group())

                # 4.3. Xử lý Danh mục (Ánh xạ sang tiếng Anh)
                cat_raw = str(row.get('category', '')).strip().lower()
                cat_str = category_map.get(cat_raw, 'other') # Mặc định là other nếu không khớp
                
                # 4.4. Xử lý Loại (Ánh xạ sang tiếng Anh)
                type_raw = str(row.get('type', '')).strip().lower()
                type_str = type_map.get(type_raw, 'expense') # Mặc định là expense nếu không khớp
                    
            except Exception as e:
                current_app.logger.debug(f"Lỗi parse dòng CSV: {row} - Error: {str(e)}")
                count_error += 1
                continue 
                
            trans = Transaction(
                user_id=current_user.id,
                wallet_id=default_wallet_id,
                date=date_obj,
                description=desc_str,
                amount=amount_val,
                category=cat_str,
                type=type_str
            )
            batch.append(trans)
            count_success += 1
            
            if len(batch) >= 500:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []
                
        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()
            
        msg = f'Đã nhập thành công {count_success} giao dịch.'
        if count_error > 0:
            msg += f' Có {count_error} dòng bị bỏ qua do sai định dạng dữ liệu.'
            flash(msg, 'warning') 
        else:
            flash(msg, 'success') 
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi Import CSV: {str(e)}")
        flash(f'Lỗi xử lý file: {str(e)}', 'danger')

    return redirect(url_for('transactions.list_transactions'))