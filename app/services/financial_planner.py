from collections import defaultdict
from datetime import datetime
import calendar

from sqlalchemy import func
from app.models import Transaction

class FinancialPlanner:
    """
    Gợi ý phân bổ ngân sách dựa trên:
    1. Lịch sử chi tiêu TRUNG BÌNH MỖI THÁNG.
    2. Tỷ lệ tiết kiệm do người dùng thiết lập cho TỪNG DANH MỤC.
    3. Lạm phát cá nhân dựa trên khu vực kinh tế (VN/Global).
    """

    INFLATION_RATES = {
        'vn': {
            'food': 0.045, 'transport': 0.030, 'education': 0.055,
            'entertainment': 0.035, 'shopping': 0.040, 'bills': 0.050, 'other': 0.040
        },
        'global': {
            'food': 0.035, 'transport': 0.025, 'education': 0.060,
            'entertainment': 0.030, 'shopping': 0.025, 'bills': 0.045, 'other': 0.030
        }
    }

    def __init__(self, user_id, db_session):
        self.user_id = user_id
        self.db_session = db_session
        self.categories = ['food', 'transport', 'education', 'entertainment',
                           'shopping', 'bills', 'other']
        self.default_weights = {
            'food': 0.30, 'transport': 0.15, 'education': 0.15,
            'entertainment': 0.10, 'shopping': 0.10, 'bills': 0.15, 'other': 0.05,
        }
        self.historical_expenses = self._get_historical_expenses()

    def _get_historical_expenses(self):
        rows = self.db_session.query(
            Transaction.category,
            func.strftime('%Y-%m', Transaction.date).label('ym'),
            func.sum(Transaction.amount).label('total'),
        ).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == 'expense',
        ).group_by(
            Transaction.category,
            func.strftime('%Y-%m', Transaction.date)
        ).all()

        active_months = set()
        cat_monthly = defaultdict(dict)

        for cat, ym, total in rows:
            active_months.add(ym)
            cat_monthly[cat][ym] = float(total)

        n_months = max(len(active_months), 1)

        expenses = {}
        for cat in self.categories:
            total_spent = sum(cat_monthly[cat].values())
            expenses[cat] = total_spent / n_months
        return expenses

    def get_personal_inflation_rate(self, region='vn'):
        rates = self.INFLATION_RATES.get(region, self.INFLATION_RATES['vn'])
        baseline_inflation = sum(rates.values()) / len(rates)
        
        total_hist = sum(self.historical_expenses.values())
        if total_hist <= 0:
            return baseline_inflation

        personal_rate = 0.0
        for cat in self.categories:
            weight = self.historical_expenses.get(cat, 0) / total_hist
            cat_inflation = rates.get(cat, baseline_inflation)
            personal_rate += weight * cat_inflation
            
        return personal_rate

    def suggest_budgets(self, monthly_income, category_savings=None, region='vn', **kwargs):
        """
        Thuật toán phân bổ ngân sách:
        1. Tính tỷ lệ chi tiêu cơ sở (kết hợp lịch sử và mặc định).
        2. Áp dụng tỷ lệ cắt giảm để dành tiền tiết kiệm.
        3. Cộng thêm lạm phát vào chi phí.
        4. Đảm bảo tổng chi tiêu không vượt quá thu nhập.
        5. Làm tròn an toàn và tính toán tiền tiết kiệm thực tế.
        """
        try:
            monthly_income = float(monthly_income)
        except (TypeError, ValueError):
            raise ValueError('Thu nhập không hợp lệ.')
        if monthly_income <= 0:
            raise ValueError('Thu nhập phải lớn hơn 0.')

        # Buoc 1: Ty le co so co Lam min (Smoothing) de khang Outlier
        total_hist = sum(self.historical_expenses.values())
        base_ratios = {}
        
        if total_hist <= 0:
            base_ratios = {cat: self.default_weights.get(cat, 0.05) for cat in self.categories}
        else:
            for cat in self.categories:
                hist_weight = self.historical_expenses.get(cat, 0) / total_hist
                default_weight = self.default_weights.get(cat, 0.05)
                # Tron 70% lich su va 30% mac dinh de triet tieu cac giao dich khung
                base_ratios[cat] = (hist_weight * 0.7) + (default_weight * 0.3)

        # Buoc 2: Ap dung ty le tiet kiem tung danh muc (KHONG CHUAN HOA LAI TONG)
        if category_savings:
            for cat in self.categories:
                try:
                    rate = float(category_savings.get(cat, 0)) / 100.0
                except (TypeError, ValueError):
                    rate = 0.0
                rate = max(0.0, min(rate, 0.95))
                base_ratios[cat] = base_ratios[cat] * (1 - rate)

        # Buoc 3 & 4: Tinh so tien va Ap dung lam phat
        personal_inflation = self.get_personal_inflation_rate(region)
        rates = self.INFLATION_RATES.get(region, self.INFLATION_RATES['vn'])
        
        exact_budgets = {}
        for cat in self.categories:
            # Tien goc = Thu nhap * Ty le (sau khi tru tiet kiem)
            base_amount = monthly_income * base_ratios[cat]
            # Tien lam phat = Tien goc * Ty le lam phat cua danh muc do
            inflation_amount = base_amount * rates.get(cat, personal_inflation)
            exact_budgets[cat] = base_amount + inflation_amount

        # Buoc 5: Can bang neu tong chi vuot thu nhap
        total_spent = sum(exact_budgets.values())
        
        if total_spent > monthly_income:
            # Phai cat giam, uu tien cat tu cac muc dang chiem nhieu tien nhat
            diff = monthly_income - total_spent
            sorted_cats = sorted(self.categories, key=lambda k: exact_budgets[k], reverse=True)
            for cat in sorted_cats:
                if diff >= 0:
                    break
                if exact_budgets[cat] > 0:
                    cut = min(exact_budgets[cat], -diff)
                    exact_budgets[cat] -= cut
                    diff += cut

        # Buoc 6: Lam tron an toan den 10.000 VND
        rounded_budgets = {}
        for cat in self.categories:
            raw = exact_budgets[cat]
            if 0 < raw < 10000:
                rounded_budgets[cat] = 10000
            else:
                rounded_budgets[cat] = round(raw / 10000) * 10000

        # Can bang lai sai so lam tron lan cuoi
        final_total_spent = sum(rounded_budgets.values())
        if final_total_spent > monthly_income:
            # Neu van vuot, cat bot tu cac muc lon
            diff = monthly_income - final_total_spent
            sorted_cats = sorted(self.categories, key=lambda k: rounded_budgets[k], reverse=True)
            for cat in sorted_cats:
                if diff >= 0:
                    break
                if rounded_budgets[cat] > 0:
                    cut = min(rounded_budgets[cat], -diff)
                    rounded_budgets[cat] -= cut
                    diff += cut

        # Dam bao khong co danh muc nao bi am
        for cat in self.categories:
            rounded_budgets[cat] = max(0, rounded_budgets[cat])

        final_total_spent = sum(rounded_budgets.values())
        target_savings = max(0.0, monthly_income - final_total_spent)

        return {
            'savings': round(target_savings, 0),
            'budgets': rounded_budgets,
            'inflation_rate': round(personal_inflation * 100, 2),
            'region': region
        }

    def get_current_spending(self, month=None, year=None):
        if month is None or year is None:
            now = datetime.now()
            month, year = now.month, now.year

        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        rows = self.db_session.query(
            Transaction.category,
            func.coalesce(func.sum(Transaction.amount), 0),
        ).filter(
            Transaction.user_id == self.user_id,
            Transaction.type == 'expense',
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        ).group_by(Transaction.category).all()

        spent = {cat: 0.0 for cat in self.categories}
        for cat, total in rows:
            spent[cat] = float(total)
        return spent