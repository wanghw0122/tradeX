from datetime import datetime, timedelta
import pandas_market_calendars as mcal
import pandas as pd
import pandas_market_calendars as mcal
import pandas as pd

def get_current_date():
    """
    获取当前日期。

    返回:
        str: 当前日期的字符串表示，格式为"YYYY-MM-DD"。
    """
    return datetime.now().strftime("%Y-%m-%d")

def get_current_date_no_line():
    """
    获取当前日期。

    返回:
        str: 当前日期和时间的字符串表示，格式为"YYYYMMDD"。
    """
    return datetime.now().strftime("%Y%m%d")

def get_current_time():
    """
    获取当前时间。

    返回:
        str: 当前时间的字符串表示，格式为"HH:MM:SS"。
    """
    return datetime.now().strftime("%H:%M:%S")

def get_previous_date():
    """
    获取前一天的日期。

    返回:
        str: 前一天日期的字符串表示，格式为"YYYY-MM-DD"。
    """
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def get_previous_date_no_line():
    """
    获取前一天的日期。

    返回:
        str: 前一天日期的字符串表示，格式为"YYYY-MM-DD"。
    """
    return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

def get_day_of_week():
    """
    获取当前一周内的第几天。

    返回:
        int: 当前一周内的第几天，星期一为0，星期日为6。
    """
    return datetime.now().weekday()

def get_hour_of_day():
    """
    获取当前一天内的第几小时。

    返回:
        int: 当前一天内的第几小时，0到23。
    """
    return datetime.now().hour


def is_trading_day(current_date=None):
    # 创建A股交易日历
    shanghai_calendar = mcal.get_calendar('XSHG')

    if not current_date:
        # 获取当前日期
        current_date = pd.Timestamp.now().date()

    schedule = shanghai_calendar.schedule(start_date=current_date - pd.Timedelta(days=30), end_date=current_date)

    if schedule.empty:
        return None, None
    if schedule.index[-1].date() == current_date:
        return True, schedule.index[-2].date().strftime("%Y%m%d")
    return False, schedule.index[-1].date().strftime("%Y%m%d")
def is_trade_date(date_str):
    """
    判断给定日期是否为交易日。

    参数:
        date (str): 日期字符串，格式为"YYYY-MM-DD"。

    返回:
        bool: 如果是交易日，返回True；否则返回False。
    """
    # 创建A股交易日历
    shanghai_calendar = mcal.get_calendar('XSHG')
    current_date = pd.Timestamp(date_str).date()

    schedule = shanghai_calendar.schedule(start_date=current_date, end_date=current_date)

    return schedule.empty == False

if __name__ == "__main__":
    current_date, previous_trading_date = is_trading_day(pd.Timestamp("2025-01-17").date())
    if current_date:
        print(f"今天是交易日: {current_date}")
        print(f"前一个交易日: {previous_trading_date}")
    else:
        print("今天不是交易日")
        print(f"最近交易日: {previous_trading_date}")

    print(is_trade_date("2025-01-17"))
    print(is_trade_date("2025-01-18"))
    print(is_trade_date("2025-01-19"))
    print(is_trade_date("2025-01-20"))
    print(is_trade_date("20250117"))
    print(is_trade_date("20250118"))