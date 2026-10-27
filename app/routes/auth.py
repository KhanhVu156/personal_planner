from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, mail
from app.forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm
from app.models import User
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message

bp = Blueprint('auth', __name__)

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_token(email):
    return get_serializer().dumps(email, salt='password-reset')

def confirm_token(token, expiration=3600):
    try:
        email = get_serializer().loads(token, salt='password-reset', max_age=expiration)
    except:
        return False
    return email

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            # THÊM remember=form.remember.data
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('Email hoặc mật khẩu không chính xác.', 'danger')
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = generate_token(user.email)
            reset_url = url_for('auth.reset_token', token=token, _external=True)
            msg = Message('Yêu cầu đặt lại mật khẩu', recipients=[user.email])
            msg.body = f'''Để đặt lại mật khẩu của bạn, vui lòng truy cập đường dẫn sau:
{reset_url}

Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này.
'''
            try:
                mail.send(msg)
                flash('Một email đã được gửi với hướng dẫn đặt lại mật khẩu.', 'info')
            except Exception as e:
                current_app.logger.error(f"Mail error: {e}")
                flash('Lỗi gửi mail. Vui lòng kiểm tra lại cấu hình.', 'danger')
        else:
            flash('Không tìm thấy địa chỉ email này.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html', form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    email = confirm_token(token)
    if not email:
        flash('Mã xác nhận không hợp lệ hoặc đã hết hạn.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Không tìm thấy người dùng.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Mật khẩu của bạn đã được cập nhật. Bạn có thể đăng nhập ngay bây giờ.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form, token=token)

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.old_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Đổi mật khẩu thành công.', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Mật khẩu cũ không chính xác.', 'danger')
    return render_template('auth/change_password.html', form=form)

@bp.route('/profile')
@login_required
def profile():
    return render_template('dashboard/profile.html')