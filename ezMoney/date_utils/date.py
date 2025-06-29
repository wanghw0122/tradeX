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


def get_previous_date_by_date(input_date=None):
    """
    获取指定日期的前一天日期。若未提供日期，则获取当前日期的前一天。

    参数:
        input_date (str, 可选): 指定日期，格式为 "YYYY-MM-DD"。默认为 None。

    返回:
        str: 前一天日期的字符串表示，格式为 "YYYY-MM-DD"。
    """
    if input_date is None:
        # 若未提供日期，使用当前日期
        current_date = datetime.now()
    else:
        try:
            # 将输入日期字符串转换为 datetime 对象
            current_date = datetime.strptime(input_date, "%Y-%m-%d")
        except ValueError:
            # 若输入日期格式错误，抛出异常
            raise ValueError("输入日期格式错误，应为 'YYYY-MM-DD'")
    # 计算前一天的日期
    previous_date = current_date - timedelta(days=1)
    return previous_date.strftime("%Y-%m-%d")

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

def get_previous_trade_date(current_date = get_current_date()):
    if '-' not in current_date:
        current_date = current_date[0:4] + '-' + current_date[4:6] + '-' + current_date[6:8]
    pre_day = get_previous_date_by_date(current_date)
    is_trade, pre_date = is_trading_day(pre_day)
    if is_trade:
        return pre_day
    else:
        return pre_date

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
    start_time = now.replace(hour=9, minute=26, second=15, microsecond=0)
    end_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
    return start_time <= now < end_time

def is_after_929():
    now = datetime.now()
    start_time = now.replace(hour=9, minute=29, second=40, microsecond=0)
    return now > start_time

def is_after_920():
    now = datetime.now()
    start_time = now.replace(hour=9, minute=20, second=0, microsecond=0)
    return now > start_time

def is_after_1300():
    now = datetime.now()
    start_time = now.replace(hour=13, minute=0, second=0, microsecond=0)
    return now > start_time

def is_after_1505():
    now = datetime.now()
    start_time = now.replace(hour=15, minute=5, second=0, microsecond=0)
    return now > start_time


def is_before_0930():
    now = datetime.now()
    start_time = now.replace(hour=9, minute=30, second=15, microsecond=0)
    return now < start_time

def is_after_0935():
    now = datetime.now()
    start_time = now.replace(hour=11, minute=30, second=0, microsecond=0)
    return now > start_time


def is_between_1500_and_1510():
    now = datetime.now()
    start_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=15, minute=10, second=0, microsecond=0)
    return start_time <= now < end_time

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

def get_trade_dates_by_start(start_date, trade_days = 30):
    import datetime
    start_date_t = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    if str(start_date_t) != start_date:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD")
    # 如果当前日期不在交易日期列表内，则当前日期天数加一
    while str(start_date_t) not in trade_date_list:
        start_date_t = start_date_t + datetime.timedelta(days=1)
    start_date_index = trade_date_list.index(str(start_date_t))
    return trade_date_list[start_date_index:start_date_index + trade_days]

def find_next_nth_date(date_key, n = 10):
    return get_trade_dates_by_start(date_key, trade_days=n)[-1]



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
    # print(is_trading_day("2025-03-03"))

    # print(get_trade_dates_by_end("2025-03-01"))
    # print(find_next_nth_date('2025-05-05', 10))
    print(get_previous_trade_date('2025-06-17'))