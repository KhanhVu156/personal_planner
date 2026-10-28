from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db
from datetime import datetime, timedelta
import calendar
from sqlalchemy import func

from app.models import Transaction, Budget, Task

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    try:
        user_id = current_user.id
        today = datetime.now()
        month = request.args.get('month', today.month, type=int)
        year = request.args.get('year', today.year, type=int)

        # 1. Tổng thu/chi toàn thời gian
        totals = db.session.query(
            Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(Transaction.user_id == user_id).group_by(Transaction.type).all()
        
        total_income = next((float(t[1]) for t in totals if t[0] == 'income'), 0.0)
        total_expense = next((float(t[1]) for t in totals if t[0] == 'expense'), 0.0)
        balance = total_income - total_expense

        # 2. Thu/chi tháng đã chọn
        month_totals = db.session.query(
            Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == user_id,
            func.extract('month', Transaction.date) == month,
            func.extract('year', Transaction.date) == year
        ).group_by(Transaction.type).all()

        income_month = next((float(t[1]) for t in month_totals if t[0] == 'income'), 0.0)
        expense_month = next((float(t[1]) for t in month_totals if t[0] == 'expense'), 0.0)

        # 3. Chi tiêu theo category
        cat_exp = db.session.query(
            Transaction.category, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            func.extract('month', Transaction.date) == month,
            func.extract('year', Transaction.date) == year
        ).group_by(Transaction.category).all()
        cat_exp_dict = {cat: float(total) for cat, total in cat_exp}

        # 4. Lấy Ngân sách & Task
        budgets = Budget.query.filter_by(user_id=user_id, month=month, year=year).all()
        budget_dict = {b.category: float(b.amount) for b in budgets}

        upcoming_tasks = Task.query.filter_by(user_id=user_id) \
            .filter(Task.status.in_(['pending', 'in_progress'])) \
            .order_by(Task.deadline.asc()).limit(5).all()
        tasks_data = [{
            'id': t.id, 'title': t.title, 'deadline': t.deadline.strftime('%d/%m/%Y'), 'progress': t.progress
        } for t in upcoming_tasks]

        # ==================== CÁC TÍNH NĂNG THAY THẾ AI ====================

        # 🚀 1. INSIGHTS (Thông tin chi tiêu)
        insights = []
        cat_names = {'food': 'Ăn uống', 'transport': 'Di chuyển', 'education': 'Học tập', 'entertainment': 'Giải trí', 'shopping': 'Mua sắm', 'bills': 'Hóa đơn', 'other': 'Khác'}
        
        if cat_exp_dict:
            top_cat = max(cat_exp_dict, key=cat_exp_dict.get)
            top_amt = cat_exp_dict[top_cat]
            insights.append(f"Danh mục '{cat_names.get(top_cat, top_cat)}' chiếm nhiều nhất ({top_amt:,.0f} VNĐ).")

        # So sánh với tháng trước
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_expense = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            func.extract('month', Transaction.date) == prev_month,
            func.extract('year', Transaction.date) == prev_year
        ).scalar()
        
        if prev_expense > 0:
            diff_pct = ((expense_month - prev_expense) / prev_expense) * 100
            if diff_pct > 0:
                insights.append(f"Chi tiêu tháng này tăng {diff_pct:.0f}% so với tháng trước.")
            elif diff_pct < 0:
                insights.append(f"Tuyệt vời! Chi tiêu tháng này giảm {abs(diff_pct):.0f}% so với tháng trước.")
        
        # 🚀 2. BURN RATE (Tốc độ đốt tiền)
        _, days_in_month = calendar.monthrange(year, month)
        current_day = today.day if (today.month == month and today.year == year) else days_in_month
        daily_avg = expense_month / current_day if current_day > 0 else 0
        projected_expense = daily_avg * days_in_month
        
        burn_rate = {
            'daily_avg': daily_avg,
            'projected': projected_expense,
            'days_left': days_in_month - current_day
        }

        # 🚀 3. DỰ BÁO 7 NGÀY TỚI (Moving Average)
        start_30 = today.date() - timedelta(days=30)
        food_30_sum = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.category == 'food',
            Transaction.type == 'expense',
            Transaction.date >= start_30
        ).scalar()
        
        food_daily_avg = float(food_30_sum) / 30.0
        forecast_data = []
        for i in range(1, 8):
            future_date = today.date() + timedelta(days=i)
            multiplier = 1.3 if future_date.weekday() >= 5 else 1.0 # Cuối tuần chi nhiều hơn
            forecast_data.append(food_daily_avg * multiplier)

        data = {
            'income': income_month,
            'expenses': expense_month,
            'balance': balance,
            'budgets': budget_dict,
            'cat_expenses': cat_exp_dict,
            'tasks': tasks_data,
            'month': month, 
            'year': year,
            'insights': insights,
            'burn_rate': burn_rate,
            'forecast': forecast_data
        }
        
        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    except Exception as e:
        current_app.logger.error(f"Lỗi API Dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Xóa API /predict cũ, thay bằng thông báo
@bp.route('/predict', methods=['GET'])
def predict():
    return jsonify({'status': 'disabled', 'message': 'AI has been replaced by SQL Forecasting'})

@bp.route('/financial-plan', methods=['POST'])
@login_required
def financial_plan():
    try:
        from app.services.financial_planner import FinancialPlanner
        data = request.get_json(silent=True) or {}
        if not data: return jsonify({'error': 'Dữ liệu trống'}), 400
            
        monthly_income = data.get('monthly_income')
        if not monthly_income or monthly_income <= 0: return jsonify({'error': 'Thu nhập không hợp lệ'}), 400

        planner = FinancialPlanner(current_user.id, db.session)
        suggestion = planner.suggest_budgets(
            monthly_income, savings_goal=data.get('savings_goal'),
            savings_percent=data.get('savings_percent'), category_weights=data.get('category_weights')
        )
        return jsonify(suggestion)
    except Exception as e:
        current_app.logger.error(f"Lỗi API Financial Plan: {str(e)}")
        return jsonify({'error': f"Lỗi máy chủ: {str(e)}"}), 500