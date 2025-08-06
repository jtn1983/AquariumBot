# utils/helpers.py

from datetime import datetime
from dateutil.relativedelta import relativedelta

def get_last_months(n=6):
    now = datetime.now().replace(day=1, hour=0, minute=0, second=0)
    return [(now - relativedelta(months=i)).strftime("%m.%Y") for i in range(n)]