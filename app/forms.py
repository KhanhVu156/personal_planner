from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, DateField,
    SelectField, TextAreaField, IntegerField, BooleanField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, ValidationError,
    NumberRange, InputRequired, Optional,
)
from app.models import User


def _norm_email(value):
    return value.strip().lower() if isinstance(value, str) else value

def _norm_username(value):
    return value.strip() if isinstance(value, str) else value

def parse_vnd_amount(value):
    """Chuyển "10.000.000" thành 10000000.0"""
    if not value:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        # Loại bỏ dấu chấm (phân cách hàng nghìn) và dấu phẩy
        clean_val = str(value).replace('.', '').replace(',', '').strip()
        return float(clean_val)
    except ValueError:
        return None


class RegistrationForm(FlaskForm):
    username = StringField('Tên đăng nhập', validators=[DataRequired(), Length(min=3, max=64)], filters=[_norm_username])
    email = StringField('Email', validators=[DataRequired(), Email()], filters=[_norm_email])
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
    email = StringField('Email', validators=[DataRequired(), Email()], filters=[_norm_email])
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    remember = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')


class WalletForm(FlaskForm):
    """Form Thêm/Sửa Ví."""
    name = StringField('Tên ví', validators=[
        DataRequired(message='Vui lòng nhập tên ví.'),
        Length(max=100, message='Tên ví không được vượt quá 100 ký tự.')
    ], render_kw={"placeholder": "VD: Tiền mặt, VietinBank, Momo..."})
    
    wallet_type = SelectField('Loại ví', choices=[
        ('cash', 'Tiền mặt'),
        ('bank', 'Tài khoản Ngân hàng'),
        ('ewallet', 'Ví điện tử (Momo, ZaloPay...)'),
        ('credit', 'Thẻ tín dụng')
    ], validators=[DataRequired()])
    
    initial_balance = StringField(
        'Số dư ban đầu (VNĐ)', 
        validators=[
            Optional(),
            NumberRange(min=0, max=1000000000000, message="Số dư không hợp lệ.")
        ],
        filters=[parse_vnd_amount],
        render_kw={"placeholder": "Nhập số tiền"} 
    )
    
    submit = SubmitField('Lưu thông tin ví')


CATEGORY_CHOICES = [
    ('food', 'Ăn uống'), ('transport', 'Di chuyển'), ('education', 'Học tập'),
    ('entertainment', 'Giải trí'), ('shopping', 'Mua sắm'), ('bills', 'Hóa đơn'),
    ('salary', 'Lương'), ('other', 'Khác'),
]
INCOME_CATEGORIES = {'salary', 'other'}
EXPENSE_CATEGORIES = {'food', 'transport', 'education', 'entertainment', 'shopping', 'bills', 'other'}


class TransactionForm(FlaskForm):
    """Form Thêm/Sửa Giao dịch."""
    date = DateField('Ngày', validators=[DataRequired()], format=['%Y-%m-%d', '%m/%d/%Y'])
    
    # ✅ FIX: Chuyển DataRequired thành Optional để cho phép không chọn ví
    wallet_id = SelectField('Thanh toán bằng', coerce=int, validators=[
        Optional() 
    ])
    
    description = StringField('Mô tả', validators=[DataRequired(), Length(max=200)])
    
    amount = StringField('Số tiền', validators=[
        DataRequired(),
        NumberRange(min=1000, max=10000000000, message="Số tiền phải từ 1.000 đến 10.000.000.000 VNĐ.")
    ], filters=[parse_vnd_amount])
    
    category = SelectField('Danh mục', choices=CATEGORY_CHOICES)
    type = SelectField('Loại', choices=[('expense', 'Chi tiêu'), ('income', 'Thu nhập')])
    submit = SubmitField('Lưu giao dịch')

    def validate_type(self, field):
        if field.data not in ('expense', 'income'):
            raise ValidationError('Loại giao dịch không hợp lệ.')

    def validate_category(self, field):
        cat = field.data
        loai = self.type.data
        if loai == 'income' and cat not in INCOME_CATEGORIES:
            raise ValidationError('Thu nhập chỉ có thể là "Lương" hoặc "Khác".')
        elif loai == 'expense' and cat not in EXPENSE_CATEGORIES:
            raise ValidationError('Danh mục "Lương" không áp dụng cho chi tiêu.')


class BudgetForm(FlaskForm):
    category = SelectField('Danh mục', choices=[
        ('food', 'Ăn uống'), ('transport', 'Di chuyển'), ('education', 'Học tập'),
        ('entertainment', 'Giải trí'), ('shopping', 'Mua sắm'), ('bills', 'Hóa đơn'), ('other', 'Khác'),
    ])
    month = SelectField('Tháng', choices=[(str(i), f'Tháng {i}') for i in range(1, 13)], validators=[DataRequired()])
    year = IntegerField('Năm', validators=[DataRequired(), NumberRange(min=2020, max=2100)])
    amount = StringField('Số tiền ngân sách', validators=[DataRequired(), NumberRange(min=1000)], filters=[parse_vnd_amount])
    submit = SubmitField('Thiết lập')


class TaskForm(FlaskForm):
    title = StringField('Tiêu đề', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Mô tả', validators=[Optional()])
    deadline = DateField('Hạn chót', validators=[DataRequired()], format=['%Y-%m-%d', '%m/%d/%Y'])
    status = SelectField('Trạng thái', choices=[('pending', 'Chờ xử lý'), ('in_progress', 'Đang thực hiện'), ('done', 'Hoàn thành')])
    progress = IntegerField('Tiến độ (%)', validators=[InputRequired(), NumberRange(min=0, max=100)], default=0)
    milestone = SelectField('Cột mốc quan trọng', choices=[(0, 'Không'), (1, 'Có')], coerce=int)
    submit = SubmitField('Lưu')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()], filters=[_norm_email])
    submit = SubmitField('Gửi Link Đặt Lại')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Mật khẩu mới', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Xác nhận mật khẩu', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Đặt lại mật khẩu')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Mật khẩu cũ', validators=[DataRequired()])
    new_password = PasswordField('Mật khẩu mới', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Xác nhận mật khẩu mới', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Đổi mật khẩu')