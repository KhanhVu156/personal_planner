from collections import defaultdict
from datetime import datetime
import calendar

from sqlalchemy import func
from app.models import Transaction

class FinancialPlanner:
    """
    Gợi ý phân bổ ngân sách dựa trên:
    1. Lịch sử chi tiêu TRUNG BÌNH MỖI THÁNG.
    2. Trọng số ưu tiên người dùng nhập.
    3. Mục tiêu tiết kiệm.
    4. Lạm phát cá nhân dựa trên khu vực kinh tế (VN/Global).
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

    def suggest_budgets(self, monthly_income, savings_goal=None,
                        savings_percent=None, category_weights=None, region='vn'):
        # --- 1. Validate input ---
        try:
            monthly_income = float(monthly_income)
        except (TypeError, ValueError):
            raise ValueError('Thu nhập không hợp lệ.')
        if monthly_income <= 0:
            raise ValueError('Thu nhập phải lớn hơn 0.')

        # --- 2. Xử lý mục tiêu tiết kiệm ---
        personal_inflation = self.get_personal_inflation_rate(region)

        if savings_goal is not None:
            try:
                target_savings = float(savings_goal)
            except (TypeError, ValueError):
                target_savings = monthly_income * 0.2
            target_savings = max(0.0, min(target_savings, monthly_income))
        elif savings_percent is not None:
            try:
                pct = float(savings_percent)
            except (TypeError, ValueError):
                pct = 20.0
            pct = max(0.0, min(pct, 95.0))
            target_savings = monthly_income * (pct / 100.0)
        else:
            target_savings = monthly_income * 0.2

        remaining = max(0.0, monthly_income - target_savings)

        # --- 3. Tỷ lệ cơ sở ---
        total_hist = sum(self.historical_expenses.values())
        if total_hist <= 0:
            base_ratios = {cat: self.default_weights.get(cat, 0.05) for cat in self.categories}
        else:
            base_ratios = {}
            for cat in self.categories:
                h = self.historical_expenses.get(cat, 0.0)
                if h > 0:
                    base_ratios[cat] = h / total_hist
                else:
                    base_ratios[cat] = self.default_weights.get(cat, 0.05) * 0.5

        # --- 4. Áp trọng số người dùng ---
        if category_weights:
            weighted = {}
            for cat in self.categories:
                try:
                    w = float(category_weights.get(cat, 1.0))
                except (TypeError, ValueError):
                    w = 1.0
                w = max(0.0, w)
                weighted[cat] = base_ratios[cat] * w

            total_w = sum(weighted.values())
            if total_w > 0:
                base_ratios = {c: weighted[c] / total_w for c in self.categories}
            else:
                # Nếu user nhập toàn số 0, fallback về default
                base_ratios = {cat: self.default_weights.get(cat, 0.05) for cat in self.categories}

        # Chuẩn hóa lần cuối
        total_base = sum(base_ratios.values())
        if total_base > 0:
            base_ratios = {c: v / total_base for c, v in base_ratios.items()}

        # --- 5. TÍNH TOÁN PHÂN BỔ CÓ LẠM PHÁT (FIX LỖI) ---
        rates = self.INFLATION_RATES.get(region, self.INFLATION_RATES['vn'])
        
        # Tạo tỷ lệ điều chỉnh dựa trên lạm phát. 
        # Ví dụ: Food có base 30%, lạm phát 4.5% -> Tỷ lệ điều chỉnh = 30% * 1.045 = 31.35%
        adjusted_ratios = {}
        for cat in self.categories:
            cat_inf = 1.0 + rates.get(cat, personal_inflation)
            adjusted_ratios[cat] = base_ratios.get(cat, 0.0) * cat_inf
            
        # Chuẩn hóa lại tổng adjusted_ratios = 1 để đảm bảo không vượt quá "remaining"
        total_adjusted = sum(adjusted_ratios.values())
        if total_adjusted > 0:
            adjusted_ratios = {c: v / total_adjusted for c, v in adjusted_ratios.items()}
        else:
            adjusted_ratios = base_ratios

        # Phân bổ tiền
        rounded_budgets = {}
        total_rounded = 0.0
        for cat in self.categories:
            raw_amount = remaining * adjusted_ratios.get(cat, 0.0)
            rounded = round(raw_amount / 10000) * 10000
            rounded_budgets[cat] = rounded
            total_rounded += rounded

        # Bù sai số làm tròn (luôn đảm bảo số dư cuối cùng không âm)
        diff = remaining - total_rounded
        if diff != 0:
            rounded_budgets['other'] = rounded_budgets.get('other', 0) + diff
            # Đề phòng trường hợp 'other' bị âm do làm tròn, ta cộng bù lại
            if rounded_budgets['other'] < 0:
                rounded_budgets['food'] += rounded_budgets['other']
                rounded_budgets['other'] = 0

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