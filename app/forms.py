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
import re

def _norm_email(value):
    return value.strip().lower() if isinstance(value, str) else value

def _norm_username(value):
    return value.strip() if isinstance(value, str) else value

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
        validators=[
            DataRequired(message='Vui lòng nhập tên đăng nhập.'), 
            Length(min=3, max=64, message='Tên đăng nhập phải từ 3 đến 64 ký tự.')
        ],
        filters=[_norm_username],
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Vui lòng nhập email.'), 
            Email(message='Địa chỉ email không hợp lệ.')
        ],
        filters=[_norm_email],
    )
    password = PasswordField('Mật khẩu', validators=[
        DataRequired(message='Vui lòng nhập mật khẩu.'), 
        Length(min=6, message='Mật khẩu phải có ít nhất 6 ký tự.')
    ])
    confirm = PasswordField('Xác nhận mật khẩu', validators=[
        DataRequired(message='Vui lòng xác nhận mật khẩu.'), 
        EqualTo('password', message='Mật khẩu xác nhận không khớp.')
    ])
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
        validators=[
            DataRequired(message='Vui lòng nhập email.'), 
            Email(message='Địa chỉ email không hợp lệ.')
        ],
        filters=[_norm_email],
    )
    password = PasswordField('Mật khẩu', validators=[DataRequired(message='Vui lòng nhập mật khẩu.')])
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
    date = DateField('Ngày', validators=[DataRequired(message='Vui lòng chọn ngày.')], format=['%Y-%m-%d', '%m/%d/%Y'])
    description = StringField('Mô tả', validators=[
        DataRequired(message='Vui lòng nhập mô tả.'), 
        Length(max=200, message='Mô tả không được vượt quá 200 ký tự.')
    ])
    
    # ✅ FIX: Đổi FloatField thành StringField
    amount = StringField(
        'Số tiền',
        validators=[
            DataRequired(message='Vui lòng nhập số tiền.'), 
            NumberRange(min=1000, max=10000000000, message="Số tiền phải từ 1.000 đến 10.000.000.000 VNĐ.")
        ],
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
        else:
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
        validators=[DataRequired(message='Vui lòng chọn tháng.')],
    )
    year = IntegerField(
        'Năm',
        validators=[
            DataRequired(message='Vui lòng nhập năm.'), 
            NumberRange(min=2020, max=2100, message='Năm phải từ 2020 đến 2100.')
        ],
    )
    
    # ✅ FIX: Đổi FloatField thành StringField
    amount = StringField(
        'Số tiền ngân sách',
        validators=[
            DataRequired(message='Vui lòng nhập số tiền ngân sách.'), 
            NumberRange(min=1000, max=10000000000, message="Số tiền phải từ 1.000 đến 10.000.000.000 VNĐ.")
        ],
        filters=[parse_vnd_amount]
    )
    submit = SubmitField('Thiết lập')


class TaskForm(FlaskForm):
    title = StringField('Tiêu đề', validators=[
        DataRequired(message='Vui lòng nhập tiêu đề.'), 
        Length(max=100, message='Tiêu đề không được vượt quá 100 ký tự.')
    ])
    description = TextAreaField('Mô tả', validators=[Optional()])
    deadline = DateField('Hạn chót', validators=[DataRequired(message='Vui lòng chọn hạn chót.')], format=['%Y-%m-%d', '%m/%d/%Y'])
    status = SelectField(
        'Trạng thái',
        choices=[('pending', 'Chờ xử lý'), ('in_progress', 'Đang thực hiện'), ('done', 'Hoàn thành')],
    )
    progress = IntegerField(
        'Tiến độ (%)',
        validators=[
            InputRequired(message='Vui lòng nhập tiến độ.'), 
            NumberRange(min=0, max=100, message='Tiến độ phải từ 0 đến 100%.')
        ],
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
        validators=[
            DataRequired(message='Vui lòng nhập email.'), 
            Email(message='Địa chỉ email không hợp lệ.')
        ],
        filters=[_norm_email],
    )
    submit = SubmitField('Gửi Link Đặt Lại')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Mật khẩu mới', validators=[
        DataRequired(message='Vui lòng nhập mật khẩu mới.'), 
        Length(min=6, message='Mật khẩu phải có ít nhất 6 ký tự.')
    ])
    confirm = PasswordField('Xác nhận mật khẩu', validators=[
        DataRequired(message='Vui lòng xác nhận mật khẩu.'), 
        EqualTo('password', message='Mật khẩu xác nhận không khớp.')
    ])
    submit = SubmitField('Đặt lại mật khẩu')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Mật khẩu cũ', validators=[DataRequired(message='Vui lòng nhập mật khẩu cũ.')])
    new_password = PasswordField('Mật khẩu mới', validators=[
        DataRequired(message='Vui lòng nhập mật khẩu mới.'), 
        Length(min=6, message='Mật khẩu phải có ít nhất 6 ký tự.')
    ])
    confirm = PasswordField(
        'Xác nhận mật khẩu mới',
        validators=[
            DataRequired(message='Vui lòng xác nhận mật khẩu mới.'), 
            EqualTo('new_password', message='Mật khẩu xác nhận không khớp.')
        ],
    )
    submit = SubmitField('Đổi mật khẩu')