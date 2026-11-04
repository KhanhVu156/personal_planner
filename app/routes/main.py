from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from app import send_email
import threading

# Khởi tạo Blueprint cho các route công khai (không cần đăng nhập)
bp = Blueprint('main', __name__)

def send_contact_email_async(app, name, email, message):
    """
    Tư duy giải thuật: Hàm này chạy trong một luồng (thread) riêng biệt.
    Mục đích là để tách biệt tác vụ gửi mail (tốn thời gian) ra khỏi luồng xử lý chính của server.
    Nhờ đó, server có thể trả về phản hồi cho người dùng ngay lập tức mà không phải chờ API.
    Cần truyền app context vì thread mới không tự động có context của Flask.
    """
    with app.app_context():
        subject = f'[Personal Planner] Yêu cầu hỗ trợ từ {name}'
        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h3 style="color: #2563eb;">Tin nhắn liên hệ mới</h3>
            <p><strong>Họ và tên:</strong> {name}</p>
            <p><strong>Email liên hệ:</strong> {email}</p>
            <p><strong>Nội dung:</strong></p>
            <div style="background-color: #f3f4f6; padding: 15px; border-left: 4px solid #2563eb; border-radius: 4px;">
                {message}
            </div>
        </div>
        """
        text_content = f"Tin nhắn liên hệ mới:\nHọ và tên: {name}\nEmail: {email}\nNội dung:\n{message}"
        
        # Gửi đến email của admin (chính là MAIL_DEFAULT_SENDER hoặc email bạn muốn nhận)
        admin_email = app.config.get('MAIL_DEFAULT_SENDER')
        send_email(subject, admin_email, html_content, text_content)

@bp.route('/')
def index():
    return render_template('landing.html')

@bp.route('/guide')
def guide():
    return render_template('pages/guide.html')

@bp.route('/privacy')
def privacy():
    return render_template('pages/privacy.html')

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # Kiểm tra xem request này có phải từ Javascript (Fetch API) gửi lên không
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not name or not email or not message:
            error_msg = 'Vui lòng điền đầy đủ thông tin.'
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
            return redirect(url_for('main.contact'))

        # Tư duy tối ưu: Kích hoạt gửi mail trong luồng riêng (background)
        app = current_app._get_current_object()
        threading.Thread(target=send_contact_email_async, args=(app, name, email, message)).start()

        # Trả về kết quả thành công ngay lập tức
        success_msg = 'Tin nhắn của bạn đã được gửi thành công. Tôi sẽ phản hồi sớm nhất có thể!'
        
        if is_ajax:
            # Trả về JSON cho Javascript xử lý
            return jsonify({'success': True, 'message': success_msg})
        
        # Fallback nếu Javascript bị tắt
        flash(success_msg, 'success')
        return redirect(url_for('main.contact'))

    return render_template('pages/contact.html')