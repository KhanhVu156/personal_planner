from collections import defaultdict
from datetime import datetime
import calendar
from zoneinfo import ZoneInfo

from sqlalchemy import func
from app.models import Transaction


class FinancialPlanner:
    """
    Gợi ý phân bổ ngân sách dựa trên:
    1. Lịch sử chi tiêu TRUNG BÌNH MỖI THÁNG (không phải mỗi giao dịch).
    2. Trọng số ưu tiên người dùng nhập.
    3. Mục tiêu tiết kiệm (số tiền tuyệt đối hoặc %).
    """

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

    # ---------------------- HISTORY ----------------------

    def _get_historical_expenses(self):
        """
        Trả về dict {category: chi tiêu trung bình mỗi tháng}.
        
        TƯ DUY TỐI ƯU: 
        - Không dùng hàm extract('month') vì nó vô hiệu hóa Index.
        - Sử dụng func.strftime('%Y-%m', ...) để group theo tháng (chuẩn SQLite).
        - SQLite không có EXTRACT, nhưng strftime chạy cực nhanh và gọn hơn.
        """
        # Group theo (category, YYYY-MM) - Tối ưu cho SQLite
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

        # Mẫu số chung: số tháng user có phát sinh chi tiêu
        n_months = max(len(active_months), 1)

        expenses = {}
        for cat in self.categories:
            total_spent = sum(cat_monthly[cat].values())
            expenses[cat] = total_spent / n_months
        return expenses

    def get_current_spending(self, month=None, year=None):
        """Chi tiêu thực tế từng category trong tháng — 1 query duy nhất."""
        if month is None or year is None:
            # ✅ FIX: Dùng giờ VN để đồng bộ với Scheduler và Dashboard
            now = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
            month, year = now.month, now.year

        # Range Query tối ưu Index
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

    # ---------------------- SUGGEST ----------------------

    def suggest_budgets(self, monthly_income, savings_goal=None,
                        savings_percent=None, category_weights=None):
        # --- 1. Validate input ---
        try:
            monthly_income = float(monthly_income)
        except (TypeError, ValueError):
            raise ValueError('Thu nhập không hợp lệ.')
        if monthly_income <= 0:
            raise ValueError('Thu nhập phải lớn hơn 0.')

        # --- 2. Mục tiêu tiết kiệm ---
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
            # ✅ Clamp 0–95% để luôn còn budget để phân bổ
            pct = max(0.0, min(pct, 95.0))
            target_savings = monthly_income * (pct / 100.0)
        else:
            target_savings = monthly_income * 0.2

        remaining = monthly_income - target_savings
        if remaining < 0:
            remaining = 0.0

        # --- 3. Tỷ lệ cơ sở ---
        total_hist = sum(self.historical_expenses.values())
        if total_hist <= 0:
            base_ratios = {cat: self.default_weights.get(cat, 0.05)
                           for cat in self.categories}
        else:
            base_ratios = {}
            for cat in self.categories:
                h = self.historical_expenses.get(cat, 0.0)
                if h > 0:
                    base_ratios[cat] = h / total_hist
                else:
                    # "Hạt giống" bằng 1/2 default cho category chưa từng chi
                    base_ratios[cat] = self.default_weights.get(cat, 0.05) * 0.5

        # Normalize
        total_base = sum(base_ratios.values())
        if total_base > 0:
            base_ratios = {c: v / total_base for c, v in base_ratios.items()}

        # --- 4. Áp trọng số người dùng ---
        if category_weights:
            weighted = {}
            for cat in self.categories:
                try:
                    w = float(category_weights.get(cat, 1.0))
                except (TypeError, ValueError):
                    w = 1.0
                w = max(0.0, w)  # chặn trọng số âm
                weighted[cat] = base_ratios[cat] * w

            total_w = sum(weighted.values())
            if total_w > 0:
                base_ratios = {c: weighted[c] / total_w for c in self.categories}
            # Nếu user nhập toàn 0 → giữ base_ratios cũ

        # --- 5. Tính tiền + làm tròn 10k ---
        rounded_budgets = {}
        total_rounded = 0.0
        for cat in self.categories:
            raw = remaining * base_ratios.get(cat, 0.0)
            rounded = round(raw / 10000) * 10000
            rounded_budgets[cat] = rounded
            total_rounded += rounded

        # --- 6. Bù sai số làm tròn vào 'other' ---
        diff = remaining - total_rounded
        if diff != 0:
            rounded_budgets['other'] = rounded_budgets.get('other', 0) + diff

        return {
            'savings': round(target_savings, 0),
            'budgets': rounded_budgets,
        }

    # ---------------------- COMPARE ----------------------

    def compare_with_suggestion(self, monthly_income, savings_goal=None,
                                 savings_percent=None, category_weights=None,
                                 month=None, year=None):
        suggestion = self.suggest_budgets(
            monthly_income, savings_goal, savings_percent, category_weights,
        )
        actual = self.get_current_spending(month, year)

        comparison = {}
        for cat in self.categories:
            actual_amt = actual.get(cat, 0.0)
            sug_amt = suggestion['budgets'].get(cat, 0.0)
            diff = actual_amt - sug_amt
            if diff > 0:
                status = 'over'
            elif diff < 0:
                status = 'under'
            else:
                status = 'on_track'
            comparison[cat] = {
                'suggested': sug_amt,
                'actual': actual_amt,
                'difference': diff,
                'status': status,
            }
        return {
            'savings': suggestion['savings'],
            'comparison': comparison,
        }