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
    return render_template('budgets.html', budgets=budgets, month=month, year=year)

@bp.route('/budgets/add', methods=['GET', 'POST'])
@login_required
def add_budget():
    form = BudgetForm()
    if form.validate_on_submit():
        existing = Budget.query.filter_by(
            user_id=current_user.id,
            category=form.category.data,
            month=form.month.data,
            year=form.year.data
        ).first()
        if existing:
            existing.amount = form.amount.data
            flash('Budget updated', 'success')
        else:
            budget = Budget(
                user_id=current_user.id,
                category=form.category.data,
                month=form.month.data,
                year=form.year.data,
                amount=form.amount.data
            )
            db.session.add(budget)
            flash('Budget added', 'success')
        db.session.commit()
        return redirect(url_for('budgets.list_budgets', month=form.month.data, year=form.year.data))
    return render_template('budget_form.html', form=form)

@bp.route('/budgets/delete/<int:id>')
@login_required
def delete_budget(id):
    budget = Budget.query.get_or_404(id)
    if budget.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('budgets.list_budgets', month=budget.month, year=budget.year))
    db.session.delete(budget)
    db.session.commit()
    flash('Budget deleted successfully', 'success')
    return redirect(url_for('budgets.list_budgets', month=budget.month, year=budget.year))