from app.models import Transaction
from sqlalchemy import func
from datetime import datetime
import calendar

class FinancialPlanner:
    def __init__(self, user_id, db_session):
        self.user_id = user_id
        self.db_session = db_session
        # Cập nhật danh sách danh mục
        self.categories = ['food', 'transport', 'education', 'entertainment', 'shopping', 'bills', 'other']
        self.historical_expenses = self._get_historical_expenses()
        
        # Tỷ lệ mặc định (Fallback) nếu người dùng chưa có lịch sử chi tiêu nào
        self.default_weights = {
            'food': 0.30, 'transport': 0.15, 'education': 0.15, 
            'entertainment': 0.10, 'shopping': 0.10, 'bills': 0.15, 'other': 0.05
        }

    def _get_historical_expenses(self):
        expenses = {}
        for cat in self.categories:
            avg = Transaction.query.filter_by(
                user_id=self.user_id, type='expense', category=cat
            ).with_entities(func.avg(Transaction.amount)).scalar()
            expenses[cat] = float(avg) if avg else 0.0
        return expenses

    def suggest_budgets(self, monthly_income, savings_goal=None, savings_percent=None, category_weights=None):
        if savings_goal is not None:
            target_savings = savings_goal
        elif savings_percent is not None:
            target_savings = monthly_income * (savings_percent / 100.0)
        else:
            target_savings = monthly_income * 0.2

        target_savings = min(target_savings, monthly_income)
        remaining = monthly_income - target_savings

        total_hist = sum(self.historical_expenses.values())
        
        # BƯỚC 1: Xác định tỷ lệ cơ sở
        if total_hist == 0:
            base_ratios = self.default_weights.copy()
        else:
            base_ratios = {}
            for cat in self.categories:
                # Nếu danh mục có lịch sử chi tiêu, dùng tỷ lệ lịch sử
                if self.historical_expenses[cat] > 0:
                    base_ratios[cat] = self.historical_expenses[cat] / total_hist
                else:
                    # Nếu chưa từng chi, cấp cho nó 1 "hạt giống" bằng 1/2 tỷ lệ mặc định
                    # Điều này đảm bảo nó không bao giờ bị bằng 0
                    base_ratios[cat] = self.default_weights.get(cat, 0.05) * 0.5 
            
            # Chuẩn hóa lại tổng = 1
            total_base = sum(base_ratios.values())
            for cat in base_ratios:
                base_ratios[cat] /= total_base

        # BƯỚC 2: Nhân với trọng số người dùng nhập (nếu có)
        if category_weights:
            for cat in self.categories:
                weight = category_weights.get(cat, 1.0)
                base_ratios[cat] *= weight
                
            # Chuẩn hóa lại tổng = 1 sau khi nhân trọng số
            total = sum(base_ratios.values())
            if total > 0:
                for cat in base_ratios:
                    base_ratios[cat] /= total

        # BƯỚC 3: Tính tiền
        budgets = {cat: remaining * base_ratios[cat] for cat in self.categories}
        
        # BƯỚC 4: LÀM TRÒN ĐẾN HÀNG CHỤC NGHÌN (10.000 VNĐ)
        rounded_budgets = {}
        total_rounded = 0
        
        for cat in self.categories:
            # Chia lấy phần nguyên của 10.000 rồi nhân lại để làm tròn (VD: 1.777.777 -> 1.780.000)
            rounded_val = round(budgets[cat] / 10000) * 10000
            rounded_budgets[cat] = rounded_val
            total_rounded += rounded_val

        # BƯỚC 5: Bù trừ sai số do làm tròn
        # Tổng sau khi làm tròn có thể bị lệch so với số tiền ban đầu (thừa/thiếu vài chục nghìn)
        # Ta sẽ cộng/trừ phần chênh lệch này vào danh mục 'other' (Khác)
        difference = remaining - total_rounded
        
        if 'other' in rounded_budgets:
            rounded_budgets['other'] += difference
        else:
            # Nếu không có danh mục other, bù vào danh mục đầu tiên
            first_cat = self.categories[0]
            rounded_budgets[first_cat] += difference

        return {
            'savings': round(target_savings, 0), # Làm tròn số tiết kiệm đến hàng đơn vị
            'budgets': rounded_budgets
        }

    def get_current_spending(self, month=None, year=None):
        if month is None:
            now = datetime.utcnow()
            month, year = now.month, now.year

        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        total_by_cat = {}
        for cat in self.categories:
            total = Transaction.query.filter_by(
                user_id=self.user_id, type='expense', category=cat
            ).filter(
                Transaction.date >= start_date, Transaction.date <= end_date
            ).with_entities(func.sum(Transaction.amount)).scalar() or 0
            total_by_cat[cat] = float(total)
        return total_by_cat

    def compare_with_suggestion(self, monthly_income, savings_goal=None, savings_percent=None, category_weights=None, month=None, year=None):
        suggestion = self.suggest_budgets(monthly_income, savings_goal, savings_percent, category_weights)
        actual = self.get_current_spending(month, year)
        comparison = {}
        for cat in self.categories:
            diff = actual.get(cat, 0) - suggestion['budgets'][cat]
            comparison[cat] = {
                'suggested': suggestion['budgets'][cat],
                'actual': actual.get(cat, 0),
                'difference': diff,
                'status': 'over' if diff > 0 else 'under' if diff < 0 else 'on_track'
            }
        return {
            'savings': suggestion['savings'],
            'comparison': comparison
        }