from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.forms import TaskForm
from app.models import Task
from datetime import datetime

bp = Blueprint('tasks', __name__)

@bp.route('/tasks')
@login_required
def list_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.deadline).all()
    return render_template('tasks.html', tasks=tasks)

@bp.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            deadline=datetime.combine(form.deadline.data, datetime.min.time()),
            status=form.status.data,
            progress=form.progress.data,
            milestone=form.milestone.data
        )
        db.session.add(task)
        db.session.commit()
        flash('Task added', 'success')
        return redirect(url_for('tasks.list_tasks'))
    return render_template('task_form.html', form=form, title='Add Task')

@bp.route('/tasks/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('tasks.list_tasks'))
    form = TaskForm(obj=task)
    if form.validate_on_submit():
        form.populate_obj(task)
        task.deadline = datetime.combine(form.deadline.data, datetime.min.time())
        db.session.commit()
        flash('Task updated', 'success')
        return redirect(url_for('tasks.list_tasks'))
    return render_template('task_form.html', form=form, title='Edit Task')

@bp.route('/tasks/delete/<int:id>')
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted', 'success')
    else:
        flash('Unauthorized', 'danger')
    return redirect(url_for('tasks.list_tasks'))

@bp.route('/tasks/update_progress/<int:id>', methods=['POST'])
@login_required
def update_progress(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    progress = data.get('progress')
    if progress is not None and 0 <= progress <= 100:
        task.progress = progress
        if progress == 100:
            task.status = 'done'
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid progress'}), 400