from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.forms import TaskForm
from app.models import Task
from datetime import datetime, date

bp = Blueprint('tasks', __name__)

def parse_boolean(val):
    """
    Hàm hỗ trợ chuyển đổi giá trị từ form sang Boolean an toàn.
    Tránh lỗi bool('0') == True trong Python.
    """
    if isinstance(val, bool): return val
    if isinstance(val, str): return val.lower() in ['1', 'true', 'yes', 'có']
    return bool(val)

@bp.route('/tasks')
@login_required
def list_tasks():
    """
    Tư duy giải thuật (Ma trận Eisenhower):
    - Sắp xếp theo 2 tiêu chí:
      1. Task.milestone.desc(): Ưu tiên các task "Quan trọng" (milestone=True) lên đầu (Trục Quan trọng).
      2. Task.deadline.asc(): Trong cùng nhóm, ưu tiên task có hạn chót gần nhất (Trục Khẩn cấp).
    - Truyền biến `today` ra template để Jinja2 tính toán số ngày còn lại.
    """
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.milestone.desc(), Task.deadline.asc()).all()
    return render_template('tasks/list.html', tasks=tasks, today=date.today())

@bp.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    """Thêm công việc mới."""
    form = TaskForm()
    if form.validate_on_submit():
        try:
            task = Task(
                user_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                # Chuyển đổi Date (từ form) sang Datetime (lưu vào DB) để đồng bộ múi giờ 00:00:00
                deadline=datetime.combine(form.deadline.data, datetime.min.time()),
                status=form.status.data,
                progress=form.progress.data,
                # Sử dụng hàm parse_boolean để tránh lỗi bool('0')
                milestone=parse_boolean(form.milestone.data)
            )
            db.session.add(task)
            db.session.commit()
            flash('Đã thêm công việc mới.', 'success')
            return redirect(url_for('tasks.list_tasks'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi thêm Task: {str(e)}")
            flash('Lỗi lưu Database. Vui lòng thử lại.', 'danger')
            
    if form.errors:
        current_app.logger.warning(f"Form Task lỗi: {form.errors}")
        
    return render_template('tasks/form.html', form=form, title='Thêm Công việc')

@bp.route('/tasks/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    """Sửa công việc. Có kiểm tra phân quyền (IDOR)."""
    task = Task.query.get_or_404(id)
    
    # Data Ownership Check
    if task.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('tasks.list_tasks'))
    
    form = TaskForm(obj=task)
    if form.validate_on_submit():
        try:
            form.populate_obj(task)
            # Form DateField trả về kiểu date, cần combine lại thành datetime cho DB
            task.deadline = datetime.combine(form.deadline.data, datetime.min.time())
            # Sử dụng hàm parse_boolean
            task.milestone = parse_boolean(form.milestone.data)
            db.session.commit()
            flash('Đã cập nhật công việc.', 'success')
            return redirect(url_for('tasks.list_tasks'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi sửa Task ID {id}: {str(e)}")
            flash('Lỗi lưu Database. Vui lòng thử lại.', 'danger')
            
    if form.errors:
        current_app.logger.warning(f"Form sửa Task lỗi: {form.errors}")
        
    return render_template('tasks/form.html', form=form, title='Sửa Công việc')


@bp.route('/tasks/delete/<int:id>', methods=['POST'])
@login_required
def delete_task(id):
    """
    Xử lý yêu cầu xóa công việc.
    TƯ DUY THIẾT KẾ: Sử dụng POST kết hợp CSRF Token để bảo vệ dữ liệu khỏi các cuộc tấn công CSRF hoặc xóa nhầm.
    """
    task = Task.query.get_or_404(id)
    
    if task.user_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này.', 'danger')
        return redirect(url_for('tasks.list_tasks'))
        
    try:
        db.session.delete(task)
        db.session.commit()
        flash('Đã xóa công việc.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi xóa Task ID {id}: {str(e)}")
        flash('Có lỗi xảy ra khi xóa. Vui lòng thử lại sau.', 'danger')
        
    return redirect(url_for('tasks.list_tasks'))


@bp.route('/tasks/update_progress/<int:id>', methods=['POST'])
@login_required
def update_progress(id):
    """
    API AJAX cập nhật tiến độ công việc (từ thanh trượt Slider).
    TƯ DUY: Xử lý logic tự động chuyển trạng thái (Status) dựa trên phần trăm tiến độ.
    """
    task = Task.query.get_or_404(id)
    if task.user_id != current_user.id:
        return jsonify({'error': 'Không có quyền'}), 403
        
    data = request.get_json()
    progress = data.get('progress')
    
    # Validate dữ liệu đầu vào cực kỳ quan trọng vì đây là API nhận JSON từ Client
    if progress is not None and isinstance(progress, int) and 0 <= progress <= 100:
        try:
            task.progress = progress
            
            # Logic tự động hóa trạng thái
            if progress == 100:
                task.status = 'done'
            elif progress < 100 and task.status == 'done':
                task.status = 'in_progress'
                
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Lỗi cập nhật tiến độ Task {id}: {str(e)}")
            return jsonify({'error': 'Lỗi DB'}), 500
            
    return jsonify({'error': 'Tiến độ không hợp lệ'}), 400