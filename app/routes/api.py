from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db, cache
from datetime import datetime, timedelta
import calendar
from sqlalchemy import func
from zoneinfo import ZoneInfo

from app.models import Transaction, Budget, Task

bp = Blueprint('api', __name__, url_prefix='/api')

VN_TZ = ZoneInfo('Asia/Ho_Chi_Minh')


@bp.route('/dashboard-stats', methods=['GET'])
@login_required
@cache.cached(timeout=120, query_string=True) # ✅ CACHE: Lưu kết quả 2 phút. query_string=True đảm bảo cache riêng cho từng tháng/năm.
def get_dashboard_stats():
    """
    API lấy toàn bộ dữ liệu cho Dashboard.
    
    TƯ DUY TỐI ƯU (Performance):
    1. Sử dụng Range Query (start_date, end_date) thay vì extract() để tận dụng DB Index.
    2. Cache kết quả trong 2 phút (timeout=120) để tránh query liên tục khi user F5.
    3. Dùng thuật toán Weekday Moving Average cho dự báo chi tiêu.
    """
    try:
        user_id = current_user.id
        today_vn = datetime.now(VN_TZ)
        
        month = request.args.get('month', today_vn.month, type=int)
        year = request.args.get('year', today_vn.year, type=int)

        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        # ==================== 1. TỔNG THU/CHI TOÀN THỜI GIAN & THÁNG ====================
        # Tối ưu: Gom 2 query (tổng all time và tổng theo tháng) lại để xử lý gọn hơn
        totals = db.session.query(
            Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(Transaction.user_id == user_id).group_by(Transaction.type).all()
        
        total_income = next((float(t[1]) for t in totals if t[0] == 'income'), 0.0)
        total_expense = next((float(t[1]) for t in totals if t[0] == 'expense'), 0.0)
        balance = total_income - total_expense

        month_totals = db.session.query(
            Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        ).group_by(Transaction.type).all()

        income_month = next((float(t[1]) for t in month_totals if t[0] == 'income'), 0.0)
        expense_month = next((float(t[1]) for t in month_totals if t[0] == 'expense'), 0.0)

        # ==================== 2. CHI TIÊU THEO CATEGORY ====================
        cat_exp = db.session.query(
            Transaction.category, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        ).group_by(Transaction.category).all()
        cat_exp_dict = {cat: float(total) for cat, total in cat_exp}

        # ==================== 3. NGÂN SÁCH & TASK ====================
        budgets = Budget.query.filter_by(user_id=user_id, month=month, year=year).all()
        budget_dict = {b.category: float(b.amount) for b in budgets}

        upcoming_tasks = Task.query.filter_by(user_id=user_id) \
            .filter(Task.status.in_(['pending', 'in_progress'])) \
            .order_by(Task.deadline.asc()).limit(5).all()
        tasks_data = [{
            'id': t.id, 'title': t.title, 'deadline': t.deadline.strftime('%d/%m/%Y'), 'progress': t.progress
        } for t in upcoming_tasks]

        # ==================== 4. INSIGHTS (Thông tin chi tiêu) ====================
        insights = []
        cat_names = {'food': 'Ăn uống', 'transport': 'Di chuyển', 'education': 'Học tập', 'entertainment': 'Giải trí', 'shopping': 'Mua sắm', 'bills': 'Hóa đơn', 'other': 'Khác'}
        
        if cat_exp_dict:
            top_cat = max(cat_exp_dict, key=cat_exp_dict.get)
            top_amt = cat_exp_dict[top_cat]
            insights.append(f"Danh mục '{cat_names.get(top_cat, top_cat)}' chiếm nhiều nhất ({top_amt:,.0f} VNĐ).")

        # So sánh tháng trước (Dùng Range Query tối ưu Index)
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        
        prev_start_date = datetime(prev_year, prev_month, 1).date()
        prev_last_day = calendar.monthrange(prev_year, prev_month)[1]
        prev_end_date = datetime(prev_year, prev_month, prev_last_day).date()

        prev_expense = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= prev_start_date,
            Transaction.date <= prev_end_date,
        ).scalar()
        
        if prev_expense > 0:
            diff_pct = ((expense_month - prev_expense) / prev_expense) * 100
            if diff_pct > 0:
                insights.append(f"Chi tiêu tháng này tăng {diff_pct:.0f}% so với tháng trước.")
            elif diff_pct < 0:
                insights.append(f"Tuyệt vời! Chi tiêu tháng này giảm {abs(diff_pct):.0f}% so với tháng trước.")

        # ==================== 5. BURN RATE (Tốc độ đốt tiền) ====================
        _, days_in_month = calendar.monthrange(year, month)
        
        if today_vn.month == month and today_vn.year == year:
            current_day = today_vn.day
        else:
            current_day = days_in_month

        daily_avg = expense_month / current_day if current_day > 0 else 0
        projected_expense = daily_avg * days_in_month
        
        burn_rate = {
            'daily_avg': daily_avg,
            'projected': projected_expense,
            'days_left': days_in_month - current_day
        }

        # ==================== 6. DỰ BÁO 7 NGÀY TỚI (Weekday Moving Average) ====================
        # TƯ DUY: Loại bỏ hardcode 'food'. Dự báo tổng chi tiêu.
        # Giải thuật: Lấy dữ liệu 30 ngày qua, tính trung bình chi tiêu cho từng Thứ (0=Thứ 2, 6=CN).
        # Dự báo 7 ngày tới dựa trên thứ của ngày đó. Cách này học được thói quen chi tiêu (VD: cuối tuần chi nhiều).
        start_30 = today_vn.date() - timedelta(days=30)
        
        # Lấy tất cả giao dịch 30 ngày qua
        trans_30d = db.session.query(Transaction.date, Transaction.amount).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= start_30
        ).all()

        weekday_sums = {i: 0.0 for i in range(7)}
        weekday_counts = {i: 0 for i in range(7)}
        total_30d = 0.0

        for t_date, t_amount in trans_30d:
            # t_date.weekday(): 0 là Thứ 2, 6 là Chủ Nhật
            wd = t_date.weekday()
            weekday_sums[wd] += float(t_amount)
            weekday_counts[wd] += 1
            total_30d += float(t_amount)

        # Fallback: Nếu không có dữ liệu, dự báo = 0
        avg_daily = total_30d / 30.0 if total_30d > 0 else 0.0
        
        forecast_data = []
        for i in range(1, 8):
            future_date = today_vn.date() + timedelta(days=i)
            wd = future_date.weekday()
            
            if weekday_counts[wd] > 0:
                # Có dữ liệu của thứ này -> Lấy trung bình của thứ đó
                pred_val = weekday_sums[wd] / weekday_counts[wd]
            else:
                # Chưa đủ dữ liệu -> Fallback về trung bình ngày
                pred_val = avg_daily
                
            forecast_data.append(pred_val)

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


@bp.route('/financial-plan', methods=['POST'])
@login_required
def financial_plan():
    """API gợi ý phân bổ ngân sách thông minh dựa trên lịch sử chi tiêu."""
    try:
        from app.services.financial_planner import FinancialPlanner
        data = request.get_json(silent=True) or {}
        if not data: 
            return jsonify({'error': 'Dữ liệu trống'}), 400
            
        monthly_income = data.get('monthly_income')
        if not monthly_income or monthly_income <= 0: 
            return jsonify({'error': 'Thu nhập không hợp lệ'}), 400

        planner = FinancialPlanner(current_user.id, db.session)
        suggestion = planner.suggest_budgets(
            monthly_income, 
            savings_goal=data.get('savings_goal'),
            savings_percent=data.get('savings_percent'), 
            category_weights=data.get('category_weights')
        )
        return jsonify(suggestion)
    except Exception as e:
        current_app.logger.error(f"Lỗi API Financial Plan: {str(e)}")
        return jsonify({'error': f"Lỗi máy chủ: {str(e)}"}), 500