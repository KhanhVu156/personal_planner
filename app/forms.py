from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, DateField, SelectField, TextAreaField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, InputRequired
from app.models import User

class RegistrationForm(FlaskForm):
    username = StringField('Tên đăng nhập', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mật khẩu', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Xác nhận mật khẩu', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Đăng ký')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Tên đăng nhập đã tồn tại.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email đã được sử dụng.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    remember = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')

# MỞ RỘNG DANH MỤC GIAO DỊCH
CATEGORY_CHOICES = [
    ('food','Ăn uống'), 
    ('transport','Di chuyển'), 
    ('education','Học tập'),
    ('entertainment','Giải trí'),
    ('shopping','Mua sắm'),
    ('bills','Hóa đơn'),
    ('salary','Lương'), # Dành cho thu nhập
    ('other','Khác')
]

class TransactionForm(FlaskForm):
    date = DateField('Ngày', validators=[DataRequired()])
    description = StringField('Mô tả', validators=[DataRequired()])
    amount = FloatField('Số tiền', validators=[DataRequired(), NumberRange(min=0.01, message="Số tiền phải lớn hơn 0")])
    category = SelectField('Danh mục', choices=CATEGORY_CHOICES)
    type = SelectField('Loại', choices=[('expense','Chi tiêu'),('income','Thu nhập')])
    submit = SubmitField('Lưu')

class BudgetForm(FlaskForm):
    # Giữ nguyên các danh mục chi tiêu (bỏ Lương ra khỏi Ngân sách)
    category = SelectField('Danh mục', choices=[
        ('food','Ăn uống'), 
        ('transport','Di chuyển'), 
        ('education','Học tập'),
        ('entertainment','Giải trí'),
        ('shopping','Mua sắm'),
        ('bills','Hóa đơn'),
        ('other','Khác')
    ])
    month = SelectField('Tháng', choices=[(str(i), f'Tháng {i}') for i in range(1, 13)], validators=[DataRequired()])
    year = IntegerField('Năm', validators=[DataRequired(), NumberRange(min=2020, max=2100)])
    amount = FloatField('Số tiền ngân sách', validators=[DataRequired(), NumberRange(min=0.01, message="Số tiền phải lớn hơn 0")])
    submit = SubmitField('Thiết lập')

class TaskForm(FlaskForm):
    title = StringField('Tiêu đề', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Mô tả')
    deadline = DateField('Hạn chót', validators=[DataRequired()])
    status = SelectField('Trạng thái', choices=[('pending','Chờ xử lý'),('in_progress','Đang thực hiện'),('done','Hoàn thành')])
    progress = IntegerField('Tiến độ (%)', validators=[InputRequired(), NumberRange(min=0, max=100)], default=0)
    milestone = SelectField('Cột mốc quan trọng', choices=[(0, 'Không'), (1, 'Có')], coerce=int)
    submit = SubmitField('Lưu')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
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