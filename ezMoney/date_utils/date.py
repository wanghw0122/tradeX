from datetime import datetime, timedelta

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