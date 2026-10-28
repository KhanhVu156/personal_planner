from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, FloatField, DateField,
    SelectField, TextAreaField, IntegerField, BooleanField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, ValidationError,
    NumberRange, InputRequired, Optional,
)
from app.models import User
import re # ✅ Thêm thư viện re để xử lý Regex

def _norm_email(value):
    """Chuẩn hoá email: trim + lowercase."""
    return value.strip().lower() if isinstance(value, str) else value

def _norm_username(value):
    """Chuẩn hoá username: trim (giữ nguyên case)."""
    return value.strip() if isinstance(value, str) else value

# ✅ Hàm lọc số tiền: Xóa dấu chấm, phẩy để chuyển "10.000.000" thành 10000000.0
def parse_vnd_amount(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        clean_val = str(value).replace('.', '').replace(',', '').strip()
        return float(clean_val)
    except ValueError:
        return None

class RegistrationForm(FlaskForm):
    username = StringField(
        'Tên đăng nhập',
        validators=[DataRequired(), Length(min=3, max=64)],
        filters=[_norm_username],
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
        filters=[_norm_email],
    )
    password = PasswordField('Mật khẩu', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Xác nhận mật khẩu', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Đăng ký')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('Tên đăng nhập đã tồn tại.')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('Email đã được sử dụng.')


class LoginForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
        filters=[_norm_email],
    )
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    remember = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')


CATEGORY_CHOICES = [
    ('food', 'Ăn uống'),
    ('transport', 'Di chuyển'),
    ('education', 'Học tập'),
    ('entertainment', 'Giải trí'),
    ('shopping', 'Mua sắm'),
    ('bills', 'Hóa đơn'),
    ('salary', 'Lương'),
    ('other', 'Khác'),
]

INCOME_CATEGORIES = {'salary', 'other'}
EXPENSE_CATEGORIES = {'food', 'transport', 'education', 'entertainment',
                      'shopping', 'bills', 'other'}


class TransactionForm(FlaskForm):
    # ✅ FIX: Chấp nhận cả format YYYY-MM-DD (chuẩn HTML) và MM/DD/YYYY (từ trình duyệt)
    date = DateField('Ngày', validators=[DataRequired()], format=['%Y-%m-%d', '%m/%d/%Y'])
    description = StringField('Mô tả', validators=[DataRequired(), Length(max=200)])
    
    # ✅ FIX: Thêm bộ lọc filters=[parse_vnd_amount] để tự động xóa dấu chấm
    amount = FloatField(
        'Số tiền',
        validators=[DataRequired(), NumberRange(min=0.01, message="Số tiền phải lớn hơn 0")],
        filters=[parse_vnd_amount]
    )
    
    category = SelectField('Danh mục', choices=CATEGORY_CHOICES)
    type = SelectField('Loại', choices=[('expense', 'Chi tiêu'), ('income', 'Thu nhập')])
    submit = SubmitField('Lưu')

    def validate_type(self, field):
        if field.data not in ('expense', 'income'):
            raise ValidationError('Loại giao dịch không hợp lệ.')

    def validate_category(self, field):
        cat = field.data
        loai = self.type.data

        if loai == 'income':
            if cat not in INCOME_CATEGORIES:
                raise ValidationError(
                    'Thu nhập chỉ có thể là "Lương" hoặc "Khác". '
                    'Vui lòng chọn lại danh mục.'
                )
        else:  # expense
            if cat not in EXPENSE_CATEGORIES:
                raise ValidationError(
                    'Danh mục "Lương" không áp dụng cho chi tiêu. '
                    'Vui lòng chọn danh mục khác.'
                )


class BudgetForm(FlaskForm):
    category = SelectField('Danh mục', choices=[
        ('food', 'Ăn uống'),
        ('transport', 'Di chuyển'),
        ('education', 'Học tập'),
        ('entertainment', 'Giải trí'),
        ('shopping', 'Mua sắm'),
        ('bills', 'Hóa đơn'),
        ('other', 'Khác'),
    ])
    month = SelectField(
        'Tháng',
        choices=[(str(i), f'Tháng {i}') for i in range(1, 13)],
        validators=[DataRequired()],
    )
    year = IntegerField(
        'Năm',
        validators=[DataRequired(), NumberRange(min=2020, max=2100)],
    )
    amount = FloatField(
        'Số tiền ngân sách',
        validators=[DataRequired(), NumberRange(min=0.01, message="Số tiền phải lớn hơn 0")],
        filters=[parse_vnd_amount] # ✅ Áp dụng luôn cho Ngân sách
    )
    submit = SubmitField('Thiết lập')


class TaskForm(FlaskForm):
    title = StringField('Tiêu đề', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    deadline = DateField('Hạn chót', validators=[DataRequired()], format=['%Y-%m-%d', '%m/%d/%Y'])
    status = SelectField(
        'Trạng thái',
        choices=[('pending', 'Chờ xử lý'), ('in_progress', 'Đang thực hiện'), ('done', 'Hoàn thành')],
    )
    progress = IntegerField(
        'Tiến độ (%)',
        validators=[InputRequired(), NumberRange(min=0, max=100)],
        default=0,
    )
    milestone = SelectField(
        'Cột mốc quan trọng',
        choices=[(0, 'Không'), (1, 'Có')],
        coerce=int,
    )
    submit = SubmitField('Lưu')


class ForgotPasswordForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
        filters=[_norm_email],
    )
    submit = SubmitField('Gửi Link Đặt Lại')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Mật khẩu mới', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Xác nhận mật khẩu', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Đặt lại mật khẩu')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Mật khẩu cũ', validators=[DataRequired()])
    new_password = PasswordField('Mật khẩu mới', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField(
        'Xác nhận mật khẩu mới',
        validators=[DataRequired(), EqualTo('new_password')],
    )
    submit = SubmitField('Đổi mật khẩu')