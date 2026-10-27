from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
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
    return render_template('tasks/list.html', tasks=tasks)

@bp.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    form = TaskForm()
    if form.validate_on_submit():
        try:
            task = Task(
                user_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                deadline=datetime.combine(form.deadline.data, datetime.min.time()),
                status=form.status.data,
                progress=form.progress.data,
                milestone=bool(form.milestone.data)
            )
            db.session.add(task)
            db.session.commit()
            flash('Đã thêm công việc mới.', 'success')
            return redirect(url_for('tasks.list_tasks'))
        except Exception as e:
            db.session.rollback()
            print(f"LỖI DATABASE: {str(e)}")
            flash(f"Lỗi lưu Database: {str(e)}", 'danger')
            
    # IN LỖI RA TERMINAL ĐỂ DEBUG
    if form.errors:
        print("LỖI FORM:", form.errors)
        
    return render_template('tasks/form.html', form=form, title='Thêm Công việc')

@bp.route('/tasks/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('tasks.list_tasks'))
    
    form = TaskForm(obj=task)
    if form.validate_on_submit():
        try:
            form.populate_obj(task)
            task.deadline = datetime.combine(form.deadline.data, datetime.min.time())
            task.milestone = bool(form.milestone.data)
            db.session.commit()
            flash('Đã cập nhật công việc.', 'success')
            return redirect(url_for('tasks.list_tasks'))
        except Exception as e:
            db.session.rollback()
            print(f"LỖI DATABASE: {str(e)}")
            flash(f"Lỗi lưu Database: {str(e)}", 'danger')
            
    if form.errors:
        print("LỖI FORM:", form.errors)
        
    return render_template('tasks/form.html', form=form, title='Sửa Công việc')

@bp.route('/tasks/delete/<int:id>')
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
        flash('Đã xóa công việc.', 'success')
    else:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
    return redirect(url_for('tasks.list_tasks'))

@bp.route('/tasks/update_progress/<int:id>', methods=['POST'])
@login_required
def update_progress(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        return jsonify({'error': 'Không có quyền'}), 403
    data = request.get_json()
    progress = data.get('progress')
    if progress is not None and 0 <= progress <= 100:
        task.progress = progress
        if progress == 100:
            task.status = 'done'
        elif progress < 100 and task.status == 'done':
            task.status = 'in_progress'
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Tiến độ không hợp lệ'}), 400