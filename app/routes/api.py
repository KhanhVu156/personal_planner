from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db, cache
from datetime import datetime, timedelta
import calendar
from sqlalchemy import func
from zoneinfo import ZoneInfo

from app.models import Transaction, Budget, Task, Wallet

bp = Blueprint('api', __name__, url_prefix='/api')
VN_TZ = ZoneInfo('Asia/Ho_Chi_Minh')


@bp.route('/dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    try:
        user_id = current_user.id
        today_vn = datetime.now(VN_TZ)
        
        month = request.args.get('month', today_vn.month, type=int)
        year = request.args.get('year', today_vn.year, type=int)

        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        # 1. Tính tổng thu/chi (Toàn thời gian)
        totals = db.session.query(
            Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(Transaction.user_id == user_id).group_by(Transaction.type).all()
        
        total_income = next((float(t[1]) for t in totals if t[0] == 'income'), 0.0)
        total_expense = next((float(t[1]) for t in totals if t[0] == 'expense'), 0.0)
        balance = total_income - total_expense

        # 2. Tính thu/chi theo tháng được chọn
        # ✅ FIX TURSO: Dùng func.date() để ép kiểu cột date trong DB về kiểu Date trước khi so sánh
        month_totals = db.session.query(
            Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == user_id,
            func.date(Transaction.date) >= start_date,
            func.date(Transaction.date) <= end_date,
        ).group_by(Transaction.type).all()

        income_month = next((float(t[1]) for t in month_totals if t[0] == 'income'), 0.0)
        expense_month = next((float(t[1]) for t in month_totals if t[0] == 'expense'), 0.0)

        # 3. Lấy chi tiêu theo danh mục trong tháng
        cat_exp = db.session.query(
            Transaction.category, func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            func.date(Transaction.date) >= start_date,
            func.date(Transaction.date) <= end_date,
        ).group_by(Transaction.category).all()
        
        cat_exp_dict = {str(cat).strip().lower(): float(total) for cat, total in cat_exp}

        # 4. Lấy ngân sách đã thiết lập trong tháng
        budgets = Budget.query.filter_by(user_id=user_id, month=month, year=year).all()
        budget_dict = {str(b.category).strip().lower(): float(b.amount) for b in budgets}

        # 5. Lấy công việc sắp tới
        upcoming_tasks = Task.query.filter_by(user_id=user_id) \
            .filter(Task.status.in_(['pending', 'in_progress'])) \
            .order_by(Task.deadline.asc()).limit(5).all()
        
        tasks_data = []
        for t in upcoming_tasks:
            # ✅ FIX TURSO: Xử lý an toàn nếu deadline trả về dạng string
            if isinstance(t.deadline, str):
                try:
                    date_str = t.deadline.split(' ')[0].split('T')[0]
                    deadline_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    formatted_deadline = deadline_obj.strftime('%d/%m/%Y')
                except ValueError:
                    formatted_deadline = t.deadline
            else:
                formatted_deadline = t.deadline.strftime('%d/%m/%Y')

            tasks_data.append({
                'id': t.id, 'title': t.title, 'deadline': formatted_deadline, 'progress': t.progress
            })

        # 6. Phân tích (Insights)
        insights = []
        cat_names = {
            'food': 'Ăn uống', 'transport': 'Di chuyển', 'education': 'Học tập', 
            'entertainment': 'Giải trí', 'shopping': 'Mua sắm', 'bills': 'Hóa đơn', 'other': 'Khác'
        }
        
        if cat_exp_dict:
            top_cat = max(cat_exp_dict, key=cat_exp_dict.get)
            top_amt = cat_exp_dict[top_cat]
            insights.append(f"Danh mục '{cat_names.get(top_cat, top_cat)}' chiếm nhiều nhất ({top_amt:,.0f} VNĐ).")

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        
        prev_start_date = datetime(prev_year, prev_month, 1).date()
        prev_last_day = calendar.monthrange(prev_year, prev_month)[1]
        prev_end_date = datetime(prev_year, prev_month, prev_last_day).date()

        prev_expense_raw = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            func.date(Transaction.date) >= prev_start_date,
            func.date(Transaction.date) <= prev_end_date,
        ).scalar()
        
        prev_expense = float(prev_expense_raw or 0.0)
        
        if prev_expense > 0:
            diff_pct = ((expense_month - prev_expense) / prev_expense) * 100
            if diff_pct > 0:
                insights.append(f"Chi tiêu tháng này tăng {diff_pct:.0f}% so với tháng trước.")
            elif diff_pct < 0:
                insights.append(f"Tuyệt vời! Chi tiêu tháng này giảm {abs(diff_pct):.0f}% so với tháng trước.")

        # 7. Burn Rate (Tốc độ chi tiêu)
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

        # =====================================================================
        # ✅ FIX CRITICAL: DỰ BÁO CHI TIÊU (FORECAST)
        # =====================================================================
        if today_vn.month == month and today_vn.year == year:
            forecast_base_date = today_vn.date()
        else:
            forecast_base_date = end_date

        start_30 = forecast_base_date - timedelta(days=30)
        
        trans_30d = db.session.query(Transaction.date, Transaction.amount).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            func.date(Transaction.date) >= start_30,
            func.date(Transaction.date) <= forecast_base_date
        ).all()

        weekday_sums = {i: 0.0 for i in range(7)}
        weekday_counts = {i: 0 for i in range(7)}
        total_30d = 0.0

        for t_date, t_amount in trans_30d:
            # ✅ FIX TURSO: Turso trả về String, SQLite trả về Date. Xử lý cả 2.
            if isinstance(t_date, str):
                try:
                    date_str = t_date.split(' ')[0].split('T')[0]
                    t_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    continue 
            else:
                t_date_obj = t_date
                
            wd = t_date_obj.weekday()
            weekday_sums[wd] += float(t_amount)
            weekday_counts[wd] += 1
            total_30d += float(t_amount)

        avg_daily_30d = total_30d / 30.0 if total_30d > 0 else 0.0
        
        forecast_data = []
        for i in range(1, 8):
            future_date = forecast_base_date + timedelta(days=i)
            wd = future_date.weekday()
            
            if weekday_counts[wd] > 0:
                pred_val = weekday_sums[wd] / weekday_counts[wd]
            else:
                pred_val = avg_daily_30d
                
            forecast_data.append(pred_val)

        # 9. Tài sản & Ví
        active_wallets = Wallet.query.filter_by(user_id=user_id, is_active=True).all()
        total_assets = 0.0
        wallets_data = []

        if active_wallets:
            wallet_flows = db.session.query(
                Transaction.wallet_id,
                Transaction.type,
                func.coalesce(func.sum(Transaction.amount), 0)
            ).filter(
                Transaction.user_id == user_id,
                Transaction.wallet_id.isnot(None)
            ).group_by(Transaction.wallet_id, Transaction.type).all()

            for w in active_wallets:
                init_bal = float(w.initial_balance or 0.0)
                in_flow = next((float(f[2]) for f in wallet_flows if f[0] == w.id and f[1] == 'income'), 0.0)
                out_flow = next((float(f[2]) for f in wallet_flows if f[0] == w.id and f[1] == 'expense'), 0.0)
                
                current_bal = init_bal + in_flow - out_flow
                total_assets += current_bal

                wallets_data.append({
                    'id': w.id, 'name': w.name, 'wallet_type': w.wallet_type, 'balance': current_bal
                })

        data = {
            'income': income_month,
            'expenses': expense_month,
            'balance': balance,
            'total_assets': total_assets,
            'wallets': wallets_data,
            'budgets': budget_dict,
            'cat_expenses': cat_exp_dict,
            'tasks': tasks_data,
            'month': month, 'year': year,
            'insights': insights,
            'burn_rate': burn_rate,
            'forecast': forecast_data,
            'forecast_base_date': forecast_base_date.isoformat()
        }
        
        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    except Exception as e:
        current_app.logger.error(f"Lỗi API Dashboard: {str(e)}")
        # ✅ Đảm bảo đóng session nếu có lỗi để tránh treo DB
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/financial-plan', methods=['POST'])
@login_required
def financial_plan():
    try:
        from app.services.financial_planner import FinancialPlanner
        data = request.get_json(silent=True) or {}
        if not data: 
            return jsonify({'error': 'Dữ liệu trống'}), 400
            
        monthly_income = data.get('monthly_income')
        if not monthly_income or float(monthly_income) <= 0: 
            return jsonify({'error': 'Thu nhập không hợp lệ (phải lớn hơn 0)'}), 400

        category_savings = data.get('category_savings', {})
        region = data.get('region', 'vn')

        planner = FinancialPlanner(current_user.id, db.session)
        
        suggestion = planner.suggest_budgets(
            monthly_income=float(monthly_income), 
            category_savings=category_savings,
            region=region
        )
        return jsonify(suggestion)
        
    except Exception as e:
        current_app.logger.error(f"Lỗi API Financial Plan: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f"Lỗi máy chủ: {str(e)}"}), 500