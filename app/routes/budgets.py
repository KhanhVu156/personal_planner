from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.forms import BudgetForm
from app.models import Budget
from datetime import datetime

bp = Blueprint('budgets', __name__)

@bp.route('/budgets')
@login_required
def list_budgets():
    month = request.args.get('month', datetime.utcnow().month, type=int)
    year = request.args.get('year', datetime.utcnow().year, type=int)
    budgets = Budget.query.filter_by(user_id=current_user.id, month=month, year=year).all()
    return render_template('budgets/list.html', budgets=budgets, month=month, year=year)

@bp.route('/budgets/add', methods=['GET', 'POST'])
@login_required
def add_budget():
    form = BudgetForm()
    
    # ✅ FIX: Nếu là GET (bấm nút Sửa), tự động lấy dữ liệu cũ điền vào form
    if request.method == 'GET':
        req_month = request.args.get('month')
        req_year = request.args.get('year')
        req_cat = request.args.get('category')
        
        if req_month and req_year and req_cat:
            form.month.data = str(req_month)
            form.year.data = int(req_year)
            form.category.data = req_cat
            
            # Tìm ngân sách hiện tại để điền số tiền cũ
            existing = Budget.query.filter_by(
                user_id=current_user.id,
                category=req_cat,
                month=int(req_month),
                year=int(req_year)
            ).first()
            if existing:
                form.amount.data = existing.amount

    if form.validate_on_submit():
        month_val = int(form.month.data)
        year_val = int(form.year.data)

        existing = Budget.query.filter_by(
            user_id=current_user.id,
            category=form.category.data,
            month=month_val,
            year=year_val
        ).first()
        
        try:
            if existing:
                existing.amount = form.amount.data
                flash(f'Đã cập nhật ngân sách Tháng {month_val}/{year_val} thành công!', 'success')
            else:
                budget = Budget(
                    user_id=current_user.id,
                    category=form.category.data,
                    month=month_val,
                    year=year_val,
                    amount=form.amount.data
                )
                db.session.add(budget)
                flash(f'Đã thêm ngân sách Tháng {month_val}/{year_val} thành công!', 'success')
            db.session.commit()
            return redirect(url_for('budgets.list_budgets', month=month_val, year=year_val))
        except Exception as e:
            db.session.rollback()
            flash(f"Lỗi lưu DB: {str(e)}", 'danger')
            print(f"LỖI DATABASE KHI LƯU NGÂN SÁCH: {e}")
    else:
        if form.errors:
            print("LỖI FORM NGÂN SÁCH:", form.errors)

    return render_template('budgets/form.html', form=form)

@bp.route('/budgets/delete/<int:id>')
@login_required
def delete_budget(id):
    budget = Budget.query.get_or_404(id)
    if budget.user_id == current_user.id:
        db.session.delete(budget)
        db.session.commit()
        flash('Đã xóa ngân sách.', 'success')
    else:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
    return redirect(url_for('budgets.list_budgets', month=budget.month, year=budget.year))