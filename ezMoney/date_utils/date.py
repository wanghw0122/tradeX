from datetime import datetime, timedelta
from arrow import get
import pandas_market_calendars as mcal
import pandas as pd
import pandas_market_calendars as mcal
import akshare as ak


try:
    trade_date_df = ak.tool_trade_date_hist_sina()
    trade_date_list = trade_date_df["trade_date"].astype(str).tolist()
    trade_date_list.sort()
except:
    trade_date_list = []


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


def is_trading_day(current_date = get_current_date()):
    if '-' not in current_date:
        current_date = current_date[0:4] + '-' + current_date[4:6] + '-' + current_date[6:8]
    is_trade = current_date in trade_date_list
    if is_trade:
        return True, trade_date_list[trade_date_list.index(current_date) - 1]
    else:
        import datetime
        end_date_t = datetime.datetime.strptime(current_date, "%Y-%m-%d").date()
        while str(end_date_t) not in trade_date_list:  # 如果当前日期不在交易日期列表内，则当前日期天数减一
            end_date_t = end_date_t - datetime.timedelta(days=1)
        return False, str(end_date_t)


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

def is_between_925_and_930():
    now = datetime.now()
    start_time = now.replace(hour=9, minute=25, second=35, microsecond=0)
    end_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
    return start_time <= now < end_time

def is_after_929():
    now = datetime.now()
    start_time = now.replace(hour=9, minute=29, second=10, microsecond=0)
    return now > start_time

def get_trade_dates_by_end(end_date, trade_days = 30):
    import datetime
    end_date_t = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    if str(end_date_t) != end_date:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD")
    # trade_date_df = ak.tool_trade_date_hist_sina()
    # trade_date_list = trade_date_df["trade_date"].astype(str).tolist()
    # trade_date_list.sort()
    while str(end_date_t) not in trade_date_list:  # 如果当前日期不在交易日期列表内，则当前日期天数减一
        end_date_t = end_date_t - datetime.timedelta(days=1)
    start_date_index = trade_date_list.index(str(end_date_t))- trade_days + 1
    return trade_date_list[start_date_index:start_date_index + trade_days]



def get_trade_dates(start_date, end_date, trade_days = 30):
    import datetime
    if not end_date:
        end_date = get_current_date()
    if not start_date:
        return get_trade_dates_by_end(end_date, trade_days)
    end_date_t = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    if str(end_date_t) != end_date:
        raise ValueError("end date日期格式错误，应为 YYYY-MM-DD")
    start_date_t = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    if str(start_date_t)!= start_date:
        raise ValueError("start date日期格式错误，应为 YYYY-MM-DD")
    # trade_date_df = ak.tool_trade_date_hist_sina()
    # trade_date_list = trade_date_df["trade_date"].astype(str).tolist()
    # trade_date_list.sort()
    while str(end_date_t) not in trade_date_list:  # 如果当前日期不在交易日期列表内，则当前日期天数减一
        end_date_t = end_date_t - datetime.timedelta(days=1)
    while str(start_date_t) not in trade_date_list:  # 如果当前日期不在交易日期列表内，则当前日期天数减一
        start_date_t = start_date_t + datetime.timedelta(days=1)
    start_date_index = trade_date_list.index(str(start_date_t))
    end_date_index = trade_date_list.index(str(end_date_t))
    if end_date_index < start_date_index:
        return []
    rslt =  trade_date_list[start_date_index:end_date_index + 1]
    if len(rslt) < trade_days:
        return rslt
    return rslt[-trade_days:]


if __name__ == "__main__":
    
    print(trade_date_list)
    print(is_trading_day("2025-02-15"))