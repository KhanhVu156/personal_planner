from flask import Blueprint, render_template, redirect, url_for, flash, request
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
    return render_template('transactions.html', transactions=pagination)

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
        flash('Transaction added successfully', 'success')
        return redirect(url_for('transactions.list_transactions'))
    return render_template('transaction_form.html', form=form, title='Add Transaction')

@bp.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    trans = Transaction.query.get_or_404(id)
    if trans.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('transactions.list_transactions'))
    form = TransactionForm(obj=trans)
    if form.validate_on_submit():
        form.populate_obj(trans)
        db.session.commit()
        flash('Transaction updated', 'success')
        return redirect(url_for('transactions.list_transactions'))
    return render_template('transaction_form.html', form=form, title='Edit Transaction')

@bp.route('/transactions/delete/<int:id>')
@login_required
def delete_transaction(id):
    trans = Transaction.query.get_or_404(id)
    if trans.user_id == current_user.id:
        db.session.delete(trans)
        db.session.commit()
        flash('Transaction deleted', 'success')
    else:
        flash('Unauthorized', 'danger')
    return redirect(url_for('transactions.list_transactions'))

@bp.route('/transactions/import', methods=['POST'])
@login_required
def import_csv():
    if 'csv_file' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('transactions.list_transactions'))
    file = request.files['csv_file']
    if file.filename == '':
        flash('Empty file', 'danger')
        return redirect(url_for('transactions.list_transactions'))

    stream = io.StringIO(file.stream.read().decode('UTF8'), newline=None)
    csv_input = csv.DictReader(stream)
    required_fields = {'date', 'description', 'amount', 'category', 'type'}
    if not required_fields.issubset(set(csv_input.fieldnames or [])):
        flash('CSV must contain columns: date, description, amount, category, type', 'danger')
        return redirect(url_for('transactions.list_transactions'))

    count = 0
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
        db.session.add(trans)
        count += 1
    db.session.commit()
    flash(f'Imported {count} transactions', 'success')
    return redirect(url_for('transactions.list_transactions'))