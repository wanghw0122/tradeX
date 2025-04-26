# 导入 requests 库
from shlex import join
from turtle import st
import requests
# 从 http_configs 模块中导入 requests_urls 变量
from .http_configs import requests_urls
from date_utils import *
import json
from logger import logger
import functools
import time

import threading

# ... 已有代码 ...

# 定义一个锁
system_time_lock = threading.Lock()
check_user_alive_lock = threading.Lock()



def timed_lru_cache(seconds: int, maxsize: int = 128):
    def wrapper_cache(func):
        func = functools.lru_cache(maxsize=maxsize)(func)
        func.lifetime = seconds
        func.expiration = time.time() + func.lifetime

        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            if time.time() >= func.expiration:
                func.cache_clear()
                func.expiration = time.time() + func.lifetime
            return func(*args, **kwargs)

        return wrapped_func

    return wrapper_cache


def log_error(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error occurred in {func.__name__}: {e}")
            logger.error(f"Parameters: args={args}, kwargs={kwargs}")
    return wrapper

def get_result(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result is None:
            raise ValueError(f"Request failed with res: {result}")
        if 'errorcode' in result and result['errorCode'] or ('ok' in result and result['ok'] == False):
            raise ValueError(f"Request failed with errorcode: {result['errorCode']}, errormsg: {result['errorMsg']}")
        if 'result' not in result:
            raise ValueError(f"Request failed with res: {result}")
        return result['result']
    return wrapper

def get_request_confg_by_name(name):
    if name not in requests_urls:
        raise ValueError(f"Invalid name: {name}")
    return requests_urls[name]

def replace_tokens(token):
    for _, url in requests_urls.items():
        url['headers']['token'] = token

# 请求的 URL 前缀
url_prefix = "https://p-xcapi.topxlc.com"

def post_request(url, headers, cookies, data=None, max_retries=3, retry_delay=1):
    retries = 0
    while retries < max_retries:
        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=data, timeout=3)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Request failed with status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Request exception: {e}")
        retries += 1
        time.sleep(retry_delay)
    
    logger.error("Max retries exceeded. Request failed.")
    return None

@log_error
def get_request(url, headers, cookies, params=None):

    response = requests.get(url, headers=headers, cookies=cookies, params=params)
    if response.status_code != 200:
        logger.error(f"Request failed with status code: {response.status_code}")
    return response.json()



@timed_lru_cache(seconds=10)
@log_error
def check_user_alive():
    """
    检查用户是否存活。

    返回:
        dict: 响应的 JSON 数据。
    """
    # 获取请求配置
    with check_user_alive_lock:
        urlConfig = get_request_confg_by_name('check_user_alive')
        url = url_prefix + urlConfig['path']
        head = urlConfig['headers']
        cookie = urlConfig['cookies']
        timeout = urlConfig['timeout']
        post = urlConfig['method'] == 'post'
        data = {}
        if post:
            post_result = post_request(url, head, cookie, data)
            i = 0
            while post_result == None or not post_result['ok']:
                logger.info("check alive fail user is not login.")
                user_login()
                post_result = post_request(url, head, cookie, data)
                i = i + 1
                if i > 3:
                    break
            if post_result and post_result['ok']:
                logger.info("check alive success.")
            return post_result
        else:
            return get_request(url, head, cookie)


@timed_lru_cache(seconds=10)
@log_error
def system_time(formatter = ""):
    """
    获取系统时间。

    返回:
        str: 格式化后的时间字符串。
    """
    # 获取请求配置
    with system_time_lock:
        urlConfig = get_request_confg_by_name('system_time')
        url = url_prefix + urlConfig['path']
        head = urlConfig['headers']
        cookie = urlConfig['cookies']
        post = urlConfig['method'] == 'post'
        data = {}
        if post:
            sys_time_json = post_request(url, head, cookie, data)
            if sys_time_json == None:
                raise ValueError(f"Request failed with res: {sys_time_json}")
            if 'errorCode' in sys_time_json and sys_time_json['errorCode']:
                raise ValueError(f"Request failed with errorcode: {sys_time_json['errorCode']}, errormsg: {sys_time_json['errorMsg']}")
            if 'result' not in sys_time_json:
                raise ValueError(f"Request failed with res: {sys_time_json}")
            timestamp = sys_time_json['result']
            date_obj = datetime.fromtimestamp(timestamp/1000)
            return date_obj.strftime(formatter)
        else:
            raise
@log_error
def block_category_rank(date = get_current_date(), model = 0):
    """
    获取板块分类排行。

    返回:
        dict: 响应的 JSON 数据。
    """
    # 获取请求配置
    urlConfig = get_request_confg_by_name('block_category_rank')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "date": date,
        "model": model
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))

@log_error
def industry_block_rank(date = get_current_date(), model = 0):
    """
    获取行业板块排行。

    返回:
        dict: 响应的 JSON 数据。
    """
    # 获取请求配置
    urlConfig = get_request_confg_by_name('industry_block_rank')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "date": date,
        "model": model
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))

@log_error
def dynamic_index(date = get_current_date(), indexType = 0):
    """
    获取小草环境重点

    返回:
        dict: 响应的 JSON 数据。
    """
    # 获取请求配置
    urlConfig = get_request_confg_by_name('dynamic_index')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "tradeDate": date,
        "indexType": indexType
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))

@log_error
def get_code_by_xiao_cao_block(blockCodeList=[], industryBlockCodeList=[],categoryCodeList=[], exponentCodeList=[], tradeDate = get_current_date(), join_separate = ","):
    """
    获取行业的股票数据

    返回:
        dict: 响应的 JSON 数据。
    """
    # 获取请求配置
    urlConfig = get_request_confg_by_name('get_code_by_xiao_cao_block')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "blockCodeList": join_separate.join(blockCodeList),
        "industryBlockCodeList": join_separate.join(industryBlockCodeList),
        "categoryCodeList": join_separate.join(categoryCodeList),
        "exponentCodeList": join_separate.join(exponentCodeList),
        "tradeDate": tradeDate
    }

    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))

@log_error
@get_result
def get_code_by_xiao_cao_block_rank(blockCodeList="", industryBlockCodeList="",categoryCodeList="", exponentCodeList="", tradeDate = get_current_date()):
    """
    获取行业的股票数据

    返回:
        dict: 响应的 JSON 数据。
    """
    urlConfig = get_request_confg_by_name('get_code_by_xiao_cao_block')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "blockCodeList": blockCodeList,
        "industryBlockCodeList": industryBlockCodeList,
        "categoryCodeList": categoryCodeList,
        "exponentCodeList": exponentCodeList,
        "tradeDate": tradeDate
    }

    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))


@log_error
def stock_call_auction(code = "", tradeDate = get_current_date_no_line()):
    """
    获取股票的集合竞价详细数据

    返回:
        dict: 响应的 JSON 数据。
    """
    # 获取请求配置
    if code == "":
        raise ValueError(f"Invalid code: {code}")
    if tradeDate == "":
        raise ValueError(f"Invalid tradeDate: {tradeDate}")
    if '-' in tradeDate:
        tradeDate = tradeDate.replace('-', '')

    if len(tradeDate) != 8:
        raise ValueError(f"Invalid tradeDate: {tradeDate}")

    urlConfig = get_request_confg_by_name('stock_call_auction')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "code": code,
        "tradeDate": tradeDate
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))

@log_error
def xiao_cao_environment_second_line_v2(codes = [], date = get_current_date(), join_separate = ","):
    """
    获取大盘环境数据

    返回:
        dict: 响应的 JSON 数据。
    """
    # 获取请求配置
    if len(codes) == 0:
        raise ValueError(f"Invalid code: {codes}")
    urlConfig = get_request_confg_by_name('xiao_cao_environment_second_line_v2')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "code": join_separate.join(codes),
        "date": date
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))

@log_error
@get_result
def sort_v2(sortId, sortType = 1, queryType = 1, type=0, date = get_current_date(), hpqbState = 0, lpdxState = 0):
    """
    获取排序数据

    params:
        sortId: 排序ID, 37-连板接力 38-小草竞王 39-红盘起爆 40-绿盘低吸
        sortType: 排序类型， 0 倒序 1 正序
        queryType: 查询类型
        type: 类型
        date: 日期
        hpqbState: 状态
        lpdxState: 状态
    返回:
        dict: 响应的 JSON 数据。
    """
    # rslts = []
    urlConfig = get_request_confg_by_name('sort_v2')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "sortId": sortId,
        "sortType": sortType,
        "queryType": queryType,
        "type": type,
        "date": date,
        "hpqbState": hpqbState,
        "lpdxState": lpdxState
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))
    # for _ in range(1, 15):
    #     rslt = 
    #     if len(rslts) > 1:
    #         cur_rslt = rslt['result']
    #         pre_rslt = rslts[-1]['result']
    #         pree_rslt = rslts[-2]['result']
    #         if len(cur_rslt) == len(pre_rslt) and len(cur_rslt) == len(pree_rslt):
    #             if cur_rslt[0] == pre_rslt[0] and cur_rslt[0] == pree_rslt[0]:
    #                 if cur_rslt[1] == pre_rslt[1] and cur_rslt[1] == pree_rslt[1]:
    #                     if cur_rslt[2] == pre_rslt[2] and cur_rslt[2] == pree_rslt[2]:
    #                         logger.info("[sort_v2] result 3 times is same. return.")
    #                         return rslt
    #                     else:
    #                         rslts.append(rslt)
    #                         time.sleep(4)
    #                         logger.info("[sort_v2] result is not same. continue.")
    #                         continue
    #                 else:
    #                     logger.info("[sort_v2] result is not same. continue.")
    #                     rslts.append(rslt)
    #                     time.sleep(4)
    #                     continue
    #             else:
    #                 logger.info("[sort_v2] result is not same. continue.")
    #                 rslts.append(rslt)
    #                 time.sleep(4)
    #                 continue
    #         else:
    #             logger.info("[sort_v2] result is not same. continue.")
    #             rslts.append(rslt)
    #             time.sleep(4)
    #             continue
    #     else:
    #         rslts.append(rslt)
    #         logger.info("[sort_v2] results < 3. continue.")
    #         time.sleep(4)
    # return rslt


@log_error
def minute_line(code = "", adj = "bfq", freq = "1min", tradeDate = get_current_date_no_line(), count = 241):
    """
    获取分钟线数据

    返回:
        dict: 响应的 JSON 数据。
    """
    if code == "":
        raise ValueError(f"Invalid code: {code}")
    if tradeDate == "":
        raise ValueError(f"Invalid tradeDate: {tradeDate}")
    if '-' in tradeDate:
        tradeDate = tradeDate.replace('-', '')

    if len(tradeDate) != 8:
        raise ValueError(f"Invalid tradeDate: {tradeDate}")
    # 获取请求配置
    urlConfig = get_request_confg_by_name('minute_line')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "code": code,
        "adj": adj,
        "freq": freq,
        "tradeDate": tradeDate,
        "count": count
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))

@log_error
@get_result
def xiao_cao_index_v2(stockCodes = "", date = get_current_date(), hpqbState = 0, lpdxState = 0):
    """
    获取小草指数数据

    返回:
        dict: 响应的 JSON 数据。
    """
    if len(stockCodes) == 0:
        raise ValueError(f"Invalid code: {stockCodes}")
    # 获取请求配置
    urlConfig = get_request_confg_by_name('xiao_cao_index_v2')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "stockCodes": stockCodes,
        "date": date,
        "hpqbState": hpqbState,
        "lpdxState": lpdxState
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))


@log_error
@get_result
def date_kline(code = "", count = 300, freq = "D", adj = "bfq"):
    """
    获取K线数据

    返回:
        dict: 响应的 JSON 数据。
    """
    if  code == "":
        raise ValueError(f"Invalid code: {code}")
    # 获取请求配置

    urlConfig = get_request_confg_by_name('date_kline')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "code": code,
        "count": count,
        "freq": freq,
        "adj": adj
    }
    data = {"params": params}
    return post_request(url, head, cookie, data = json.dumps(data))

def user_login(loginId = "1QIgHC8Y4Z/OkUV8Av7lOQ==", passwd = "Vz53GS09rB+bsm7/8nDHgQ==", type = 0):
    """
    用户登录

    返回:
        dict: 响应的 JSON 数据。
    """
    # 获取请求配置
    urlConfig = get_request_confg_by_name('user_login')
    url = url_prefix + urlConfig['path']
    head = urlConfig['headers']
    cookie = urlConfig['cookies']
    params = {
        "loginId": loginId,
        "passwd": passwd,
        "type": type,
        "environment": "{}"
    }
    data = {"params": params}
    result = post_request(url, head, cookie, data = json.dumps(data))
    logger.info(f"user login result: {result}")
    if result == None:
        raise ValueError(f"Request failed with res: {result}")
    if 'errorcode' in result and result['errorcode']:
        raise ValueError(f"Request failed with errorcode: {result['errorcode']}, errormsg: {result['errormsg']}")
    if'result' not in result:
        raise ValueError(f"Request failed with res: {result}")
    real_result = result['result']
    if 'token' not in real_result:
        raise ValueError(f"Request failed with res: {real_result}")
    token =  real_result['token']
    logger.info(f"user login success. new token: {token}")
    replace_tokens(token)


# 如果脚本作为主程序运行
if __name__ == '__main__':
    # 调用 check_user_alive 函数并打印结果
    # print(check_user_alive())

    # print(system_time())

    # print(json.dumps(block_category_rank(date = "2025-01-10")))

    # print(json.dumps(industry_block_rank(date = "2025-01-10")))

    # print(dynamic_index(date = "2025-01-10"))

    # print(get_code_by_xiao_cao_block(industryBlockCodeList=['980364.ZHBK'],tradeDate="2025-01-10"))

    # print(json.dumps(stock_call_auction(code="002666.XSHE", tradeDate="2025-01-10")))

    print(json.dumps(xiao_cao_environment_second_line_v2(codes=['9A0001','9A0002','9A0003','9B0001','9B0002','9B0003','9C0001'], date="2025-01-10")))

    # print(sort_v2(sortId=37, sortType=1, queryType=1, type=0, date="2025-01-10", hpqbState=0, lpdxState=0))

    # print(minute_line(code="002666.XSHE", adj="bfq", freq="1min", tradeDate="2025-01-10", count=241))

    # print(xiao_cao_index_v2(stockCodes=['001314.XSHE','300280.XSHE','300323.XSHE','603118.XSHG','002137.XSHE','002397.XSHE','002582.XSHE','002265.XSHE'], date="2025-01-10", hpqbState=0, lpdxState=0))

    # print(date_kline(code="001314.XSHE", count=300, freq="D", adj="bfq"))

    pass


