from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, send_email
from app.forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm
from app.models import User
from itsdangerous import URLSafeTimedSerializer
from datetime import timedelta

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
    # Tư duy logic: Chặn người dùng đã đăng nhập vào trang đăng ký.
    # Tuy nhiên, nếu họ là tài khoản Demo và muốn nâng cấp, họ phải đi qua route /upgrade.
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
            
            # TƯ DUY FIX LỖI GHI NHỚ ĐĂNG NHẬP (FIX TRIỆT ĐỂ):
            # Mục tiêu: Nếu không tích "Ghi nhớ", đóng tab/trình duyệt là mất phiên.
            # Cách làm: 
            # 1. Ép session.permanent = False (để tạo Session Cookie tạm thời).
            # 2. Khởi tạo response và chủ động XÓA cookie 'remember_token' (nếu có từ lần trước).
            # 3. Chỉ khi tích chọn, ta mới set session.permanent = True và tạo cookie ghi nhớ.
            
            if form.remember.data:
                # Người dùng CHỌN ghi nhớ: Session sống lâu (theo config), tạo Remember Cookie
                current_app.permanent_session_lifetime = timedelta(days=30)
                session.permanent = True
                login_user(user, remember=True, duration=timedelta(days=30))
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
            else:
                # Người dùng KHÔNG CHỌN: Session tạm thời
                session.permanent = False
                login_user(user, remember=False)
                
                # Tạo response và xóa vĩnh viễn cookie remember_token cũ (nếu có) để tránh trình duyệt tự động đăng nhập lại
                next_page = request.args.get('next')
                response = redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
                response.delete_cookie('remember_token')
                return response
        else:
            flash('Email hoặc mật khẩu không chính xác.', 'danger')
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    # Tư duy UX/CRO: Kiểm tra xem người dùng đang đăng xuất có phải là tài khoản Demo hay không.
    # Phải lưu trạng thái này vào một biến trước khi gọi logout_user() 
    # vì sau khi logout, current_user sẽ trở thành AnonymousUser và thông tin email sẽ bị mất.
    is_demo_user = (current_user.email == 'demo@personalplanner.com')
    
    # Tiến hành xóa session đăng nhập (đồng thời xóa Remember Cookie)
    logout_user()
    
    if is_demo_user:
        # Nếu là tài khoản Demo: Đưa về Landing Page để họ tiếp tục xem giới thiệu sản phẩm 
        # và mời họ đăng ký tài khoản chính thức. Tránh việc đưa họ về trang Đăng nhập (gây bế tắc).
        flash('Phiên dùng thử của bạn đã kết thúc. Hãy tạo tài khoản để lưu trữ dữ liệu vĩnh viễn nhé!', 'info')
        return redirect(url_for('main.index'))
    else:
        # Nếu là người dùng thật: Đưa về trang Đăng nhập để họ có thể đăng nhập lại.
        flash('Bạn đã đăng xuất thành công.', 'success')
        return redirect(url_for('auth.login'))

@bp.route('/upgrade')
@login_required
def upgrade():
    # Tư duy giải thuật: Route này phục vụ riêng cho việc nâng cấp từ tài khoản Demo lên tài khoản chính thức.
    # Do logic bảo mật của hàm register() chặn người dùng đã đăng nhập, ta bắt buộc phải xóa Session (logout)
    # trước khi đưa họ đến trang đăng ký. Điều này giúp trải nghiệm liền mạch và tránh lỗi kẹt session.
    logout_user()
    flash('Vui lòng tạo tài khoản mới để lưu trữ dữ liệu vĩnh viễn và sử dụng toàn bộ tính năng.', 'info')
    return redirect(url_for('auth.register'))

# Route mới dành cho tính năng Dùng thử (Try it out)
@bp.route('/demo')
def demo():
    demo_user = User.query.filter_by(email='demo@personalplanner.com').first()
    
    if not demo_user:
        demo_user = User(username='Demo User', email='demo@personalplanner.com')
        demo_user.set_password('demo_password_123')
        db.session.add(demo_user)
        db.session.commit()
    
    # TƯ DUY FIX LỖI: Chế độ dùng thử không bao giờ ghi nhớ. 
    # Ép session tạm thời và xóa cookie remember_token để đảm bảo đóng tab là mất.
    session.permanent = False
    login_user(demo_user)
    
    flash('Bạn đang trải nghiệm chế độ Dùng thử với tài khoản Demo.', 'info')
    response = redirect(url_for('dashboard.index'))
    response.delete_cookie('remember_token')
    return response

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
            
            # TƯ DUY TỐI ƯU: Tạo nội dung email HTML đẹp mắt hơn thay vì chỉ text thuần.
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
                <h2 style="color: #2563eb; text-align: center;">Yêu cầu đặt lại mật khẩu</h2>
                <p>Chào bạn,</p>
                <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản liên kết với email này trên hệ thống <strong>Personal Planner</strong>.</p>
                <p>Vui lòng nhấn vào nút bên dưới để tiến hành đặt lại mật khẩu:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Đặt lại mật khẩu</a>
                </div>
                <p style="font-size: 13px; color: #6b7280;">Nếu nút trên không hoạt động, bạn có thể sao chép và dán đường dẫn sau vào trình duyệt:</p>
                <p style="font-size: 13px; color: #2563eb; word-break: break-all;">{reset_url}</p>
                <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                <p style="font-size: 12px; color: #9ca3af;">Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này. Tài khoản của bạn vẫn an toàn.</p>
            </div>
            """
            text_content = f"Để đặt lại mật khẩu của bạn, vui lòng truy cập đường dẫn sau:\n{reset_url}\n\nNếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này."
            
            # Gọi hàm send_email dùng chung
            if send_email('Yêu cầu đặt lại mật khẩu - Personal Planner', user.email, html_content, text_content):
                flash('Một email đã được gửi với hướng dẫn đặt lại mật khẩu.', 'info')
            else:
                flash('Lỗi gửi mail. Vui lòng thử lại sau.', 'danger')
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