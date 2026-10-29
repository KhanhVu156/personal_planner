from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.forms import BudgetForm
from app.models import Budget
from datetime import datetime

bp = Blueprint('budgets', __name__)

def parse_vnd_amount(amount_val):
    """
    TƯ DUY XỬ LÝ DỮ LIỆU AN TOÀN (ĐÃ FIX LỖI):
    - Nếu WTForms đã tự động ép kiểu thành float/int (VD: 10000000.0) thì trả về luôn.
    - Nếu là chuỗi (VD: "10.000.000") thì mới lọc bỏ ký tự và ép kiểu.
    """
    if amount_val is None or amount_val == '':
        return 0.0
        
    # Nếu đã là số (float hoặc int) từ WTForms, trả về luôn để tránh lỗi cộng thêm số 0
    if isinstance(amount_val, (int, float)):
        return float(amount_val)
        
    try:
        # Nếu là chuỗi, lọc bỏ mọi ký tự không phải là số
        cleaned_str = ''.join(filter(str.isdigit, str(amount_val)))
        return float(cleaned_str) if cleaned_str else 0.0
    except Exception as e:
        current_app.logger.error(f"Lỗi parse tiền tệ từ giá trị '{amount_val}': {e}")
        return 0.0

@bp.route('/budgets')
@login_required
def list_budgets():
    """Hiển thị danh sách ngân sách."""
    month_str = request.args.get('month')
    year_str = request.args.get('year')
    
    query = Budget.query.filter_by(user_id=current_user.id)
    
    if month_str and year_str:
        try:
            query = query.filter_by(month=int(month_str), year=int(year_str))
        except ValueError:
            flash('Tham số lọc không hợp lệ.', 'warning')
            return redirect(url_for('budgets.list_budgets'))
        
    budgets = query.order_by(Budget.year.desc(), Budget.month.desc(), Budget.category).all()
    
    return render_template('budgets/list.html', budgets=budgets, month=month_str, year=year_str)


@bp.route('/budgets/add', methods=['GET', 'POST'])
@login_required
def add_budget():
    """Thiết lập hoặc Cập nhật ngân sách (Upsert)."""
    form = BudgetForm()
    
    # Lấy tháng/năm hiện tại để làm giá trị mặc định cho form
    now = datetime.now()
    display_month = now.month
    display_year = now.year
    
    if request.method == 'GET':
        req_month = request.args.get('month')
        req_year = request.args.get('year')
        req_cat = request.args.get('category')
        
        if req_month and req_year and req_cat:
            form.month.data = str(req_month)
            form.year.data = int(req_year)
            form.category.data = req_cat
            display_month = req_month
            display_year = req_year
            
            existing = Budget.query.filter_by(
                user_id=current_user.id,
                category=req_cat,
                month=int(req_month),
                year=int(req_year)
            ).first()
            if existing:
                form.amount.data = f"{int(existing.amount):,}".replace(',', '.')

    if form.validate_on_submit():
        month_val = int(form.month.data)
        year_val = int(form.year.data)
        
        # Sử dụng hàm parse đã được fix
        amount_val = parse_vnd_amount(form.amount.data)
        
        current_app.logger.info(f"[DEBUG] Số tiền lưu vào DB: {amount_val}")

        existing = Budget.query.filter_by(
            user_id=current_user.id,
            category=form.category.data,
            month=month_val,
            year=year_val
        ).first()
        
        try:
            if existing:
                existing.amount = amount_val
                flash(f'Đã cập nhật ngân sách Tháng {month_val}/{year_val} thành công!', 'success')
            else:
                budget = Budget(
                    user_id=current_user.id,
                    category=form.category.data,
                    month=month_val,
                    year=year_val,
                    amount=amount_val
                )
                db.session.add(budget)
                flash(f'Đã thêm ngân sách Tháng {month_val}/{year_val} thành công!', 'success')
                
            db.session.commit()
            return redirect(url_for('budgets.list_budgets', month=month_val, year=year_val))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi lưu ngân sách: {str(e)}")
            flash(f"Lỗi lưu DB. Vui lòng thử lại.", 'danger')
    else:
        if form.errors:
            current_app.logger.warning(f"Form ngân sách lỗi: {form.errors}")

    # Truyền display_month và display_year sang template để tránh lỗi required
    return render_template('budgets/form.html', form=form, display_month=display_month, display_year=display_year)


@bp.route('/budgets/delete/<int:id>', methods=['POST'])
@login_required
def delete_budget(id):
    """Xóa ngân sách."""
    budget = Budget.query.get_or_404(id)
    req_month = request.args.get('month')
    req_year = request.args.get('year')
    
    if budget.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('budgets.list_budgets', month=req_month, year=req_year))
        
    try:
        db.session.delete(budget)
        db.session.commit()
        flash('Đã xóa ngân sách.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi xóa ngân sách ID {id}: {str(e)}")
        flash('Có lỗi xảy ra khi xóa. Vui lòng thử lại sau.', 'danger')
        
    return redirect(url_for('budgets.list_budgets', month=req_month, year=req_year))