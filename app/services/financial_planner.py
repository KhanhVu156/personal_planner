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
        TƯ DUY THUẬT TOÁN MỚI:
        1. Tính tỷ lệ chi tiêu cơ sở (dựa trên lịch sử hoặc mặc định).
        2. Áp dụng tỷ lệ cắt giảm (category_savings) của người dùng.
        3. Bù trượt giá (Inflation).
        4. Scale down nếu tổng chi tiêu vượt thu nhập.
        5. Số tiền dư ra chính là tiết kiệm.
        """
        # --- 1. Validate input ---
        try:
            monthly_income = float(monthly_income)
        except (TypeError, ValueError):
            raise ValueError('Thu nhập không hợp lệ.')
        if monthly_income <= 0:
            raise ValueError('Thu nhập phải lớn hơn 0.')

        # --- 2. Tỷ lệ cơ sở ---
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

        # --- 3. Áp dụng tỷ lệ tiết kiệm từng danh mục ---
        if category_savings:
            for cat in self.categories:
                try:
                    rate = float(category_savings.get(cat, 0)) / 100.0
                except (TypeError, ValueError):
                    rate = 0.0
                # Giới hạn tỷ lệ từ 0% đến 95% (để tránh ngân sách bằng 0)
                rate = max(0.0, min(rate, 0.95))
                base_ratios[cat] = base_ratios[cat] * (1 - rate)

        # --- 4. Áp dụng lạm phát (Bù trượt giá) ---
        personal_inflation = self.get_personal_inflation_rate(region)
        rates = self.INFLATION_RATES.get(region, self.INFLATION_RATES['vn'])
        
        for cat in self.categories:
            cat_inf = 1.0 + rates.get(cat, personal_inflation)
            base_ratios[cat] = base_ratios[cat] * cat_inf

        # --- 5. Chuẩn hóa & Giới hạn (Cap) ---
        total_base = sum(base_ratios.values())
        
        if total_base > 1.0:
            # Nếu lạm phát đẩy tổng chi tiêu vượt 100% thu nhập, scale down lại
            for cat in self.categories:
                base_ratios[cat] = base_ratios[cat] / total_base
            total_base = 1.0
        elif total_base == 0:
            # Fallback nếu user nhập toàn số 0 gây lỗi chia
            base_ratios = {cat: self.default_weights.get(cat, 0.05) for cat in self.categories}
            total_base = sum(base_ratios.values())

        # --- 6. Tính toán phân bổ số tiền (ĐÃ SỬA LỖI LÀM TRÒN) ---
        # TƯ DUY SỬA LỖI: 
        # - Code cũ làm tròn về 0 nếu số tiền < 5.000, khiến mục "Khác" biến mất.
        # - Code cũ dồn toàn bộ sai số (diff) vào "Khác", nếu âm sẽ ép "Khác" = 0.
        # - Giải pháp: Làm tròn an toàn (tối thiểu 10k nếu >0), và nếu tổng vượt thu nhập
        #   thì cắt giảm tỷ lệ thuận từ các danh mục lớn nhất.

        # 6.1 Tính số tiền chính xác
        exact_budgets = {cat: monthly_income * base_ratios[cat] for cat in self.categories}

        # 6.2 Làm tròn an toàn đến 10.000 VNĐ
        rounded_budgets = {}
        for cat in self.categories:
            raw = exact_budgets[cat]
            if 0 < raw < 10000:
                rounded_budgets[cat] = 10000 # Đảm bảo không bị mất danh mục
            else:
                rounded_budgets[cat] = round(raw / 10000) * 10000

        # 6.3 Cân bằng sai số do làm tròn
        total_spent = sum(rounded_budgets.values())
        diff = monthly_income - total_spent

        if diff < 0:
            # Nếu tổng chi vượt thu nhập (do làm tròn lên), ta phải cắt giảm.
            # Ưu tiên cắt giảm từ các danh mục đang chiếm nhiều tiền nhất.
            sorted_cats = sorted(self.categories, key=lambda k: rounded_budgets[k], reverse=True)
            
            for cat in sorted_cats:
                if diff >= 0:
                    break
                if rounded_budgets[cat] > 0:
                    # Cắt tối đa bằng số tiền hiện có của danh mục đó
                    cut = min(rounded_budgets[cat], -diff)
                    rounded_budgets[cat] -= cut
                    diff += cut

        # 6.4 Đảm bảo không có danh mục nào bị âm
        for cat in self.categories:
            rounded_budgets[cat] = max(0, rounded_budgets[cat])

        # 6.5 Tính toán tiết kiệm
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