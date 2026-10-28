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
                flash('Đã cập nhật ngân sách thành công!', 'success')
            else:
                budget = Budget(
                    user_id=current_user.id,
                    category=form.category.data,
                    month=month_val,
                    year=year_val,
                    amount=form.amount.data
                )
                db.session.add(budget)
                flash('Đã thêm ngân sách mới thành công!', 'success')
            db.session.commit()
            return redirect(url_for('budgets.list_budgets', month=month_val, year=year_val))
        except Exception as e:
            db.session.rollback()
            flash(f"Lỗi lưu DB: {str(e)}", 'danger')
            print(f"LỖI DATABASE KHI LƯU NGÂN SÁCH: {e}")
    else:
        # In lỗi form ra màn hình đen nếu có
        if form.errors:
            print("LỖI FORM NGÂN SÁCH:", form.errors)

    return render_template('budgets/form.html', form=form)