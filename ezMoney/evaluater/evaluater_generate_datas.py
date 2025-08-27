from functools import lru_cache
import logging
import sys
import datetime
sys.path.append(r"D:\workspace\TradeX\ezMoney")
from common import constants
from date_utils import date as dt
from xtquant import xttrader
import pandas as pd
import akshare as ak
import traceback
import concurrent.futures
import pandas as pd
from tqdm import tqdm
import math
import json
from pandas import Timestamp

from xtquant import xtdatacenter as xtdc
xtdc.set_token("26e6009f4de3bfb2ae4b89763f255300e96d6912")

print('xtdc.init')
xtdc.init() # 初始化行情模块，加载合约数据，会需要大约十几秒的时间
print('done')

from xtquant import xtdata 

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def build_all_stock_datas(tuple_list = None):
    # 获取股票列表
    all_stocks = {}
    all_stocks_info = xtdata.get_stock_list_in_sector('沪深A股')
    for stock in all_stocks_info:
        if stock.startswith('60') or stock.startswith('00'):
            cde = stock.split('.')[0]
            all_stocks[cde] = stock
    print(f"获取到{len(all_stocks)}只股票")

    # 准备下载任务
    tasks = []
    for datekey, stock_code in tuple_list:
        code_part = stock_code.split('.')[0]
        if code_part in all_stocks:
            converted_stock_code = all_stocks[code_part]
            tasks.append((datekey, converted_stock_code))

    # 多线程下载
    print(f"开始下载股票数据，共 {len(tasks)} 个任务...")
    results = []
    
    # 使用线程池执行任务
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 提交所有任务
        future_to_task = {
            executor.submit(build_stock_datas, stock_code, datekey): (datekey, stock_code)
            for datekey, stock_code in tasks
        }
        
        # 创建进度条
        with tqdm(total=len(tasks), desc="下载进度", unit="task") as pbar:
            for future in concurrent.futures.as_completed(future_to_task):
                datekey, stock_code = future_to_task[future]
                try:
                    data = future.result()
                    if data:
                        results.append(data)
                except Exception as e:
                    print(f"\n下载失败 [{datekey} {stock_code}]: {str(e)}")
                finally:
                    pbar.update(1)  # 更新进度条
                    pbar.set_postfix_str(f"最新: {stock_code}")

    print(f"\n所有股票数据下载完成！成功下载 {len(results)}/{len(tasks)} 个数据")
    return results

def get_stock_open_close_price(auction_code, date, next_date):
    if '-' in date or '-' in next_date:
        n_date = date.replace('-', '')
        n_next_date = next_date.replace('-', '')
    else:
        n_date = date
        n_next_date = next_date

    print(f"获取股票{auction_code} {date} {next_date} 数据")

    xtdata.download_history_data(auction_code, period='1d', start_time=n_date, end_time=n_next_date, incrementally = None)
    x1dpdata = xtdata.get_local_data(field_list=[], stock_list=[auction_code], period='1d', start_time=n_date, end_time=n_next_date, count=-1,
               dividend_type='none', fill_data=True)
    df = x1dpdata[auction_code]
    length = len(df)
    if length != 2:
        return -1, -1, -1, -1
    x_data = df.loc[n_date: n_next_date]['open'].astype(float)
    x_data_close = df.loc[n_date: n_next_date]['close'].astype(float)
    start_price = x_data[n_date]
    end_price = x_data[n_next_date]
    close_price = x_data_close[n_date]
    n_close_price = x_data_close[n_next_date]
    return start_price, close_price, end_price, n_close_price


def get_marketting_datas(stock_code, cur_date):
    trade_days = dt.get_trade_dates_by_end(cur_date, trade_days= 100)
    if not trade_days:
        return None
    n_date_key = trade_days[0].replace('-', '')
    m_date_key = trade_days[-1].replace('-', '')
    xtdata.download_history_data(stock_code, '1d', n_date_key, m_date_key)
    all_days_data = xtdata.get_market_data(stock_list=[stock_code], period='1d', start_time=n_date_key, end_time=m_date_key)
    if not all_days_data:
        return None
    res = {}
    try:
        ma5 = float(all_days_data['close'].loc[stock_code].sort_index(ascending=True).tail(5).mean())
        if ma5 and not math.isnan(ma5):
            res['ma5'] = ma5
    except Exception as e:
        pass
    try:
        ma10 = float(all_days_data['close'].loc[stock_code].sort_index(ascending=True).tail(10).mean())
        if ma10 and not math.isnan(ma10):
            res['ma10'] = ma10
    except Exception as e:
        pass
    try:
        ma20 = float(all_days_data['close'].loc[stock_code].sort_index(ascending=True).tail(20).mean())
        if ma20 and not math.isnan(ma20):
            res['ma20'] = ma20
    except Exception as e:
        pass
    try:
        ma30 = float(all_days_data['close'].loc[stock_code].sort_index(ascending=True).tail(30).mean())
        if ma30 and not math.isnan(ma30):
            res['ma30'] = ma30
    except Exception as e:
        pass
    try:
        ma60 = float(all_days_data['close'].loc[stock_code].sort_index(ascending=True).tail(60).mean())
        if ma60 and not math.isnan(ma60):
            res['ma60'] = ma60
    except Exception as e:
        pass
    
    return res


@lru_cache
def build_stock_datas(stock_code, datekey):
    # from xtquant import xtdata
    # xtdata.connect(port=58611)
    import numpy as np
    if '-' in datekey:
        n_data_key = datekey.replace('-', '')
    else:
        n_data_key = datekey

    is_trade_day, _ = dt.is_trading_day(datekey)
    if not is_trade_day:
        raise Exception(f'not trade day {stock_code} - {datekey}')

    next_trade_day = dt.find_next_nth_date(datekey, 1)
    next_next_trade_day = dt.find_next_nth_date(next_trade_day, 1)

    print(f"获取股票{stock_code} {datekey} {next_trade_day} {next_next_trade_day} 数据")

    cur_day = dt.get_current_date()

    # 字符串转日期对象（假设格式为 yyyy-MM-dd）
    next_date = datetime.datetime.strptime(next_trade_day, "%Y-%m-%d").date()
    next_next_date = datetime.datetime.strptime(next_next_trade_day, "%Y-%m-%d").date()

    current_date = datetime.datetime.strptime(cur_day, "%Y-%m-%d").date()

    # 比较转换后的日期对象
    if next_date >= current_date:
        return {}
    if next_next_date >= current_date:
        return {}
    if '-' in next_trade_day:
        l_date_key = next_trade_day.replace('-', '')
    else:
        l_date_key = next_trade_day
    
    if '-' in next_next_trade_day:
        l_next_date_key = next_next_trade_day.replace('-', '')
    else:
        l_next_date_key = next_next_trade_day


    trade_dates = dt.get_trade_dates_by_end(datekey, 5)
    if len(trade_dates) < 5:
        logger.error(f"无法获取足够的交易日数据 [{stock_code} {datekey}]")
        return {}

    for trade_date in trade_dates:
        if '-' in trade_date:
            trade_date_key = trade_date.replace('-', '')
        else:
            trade_date_key = trade_date
        xtdata.download_history_data(stock_code, 'tick', trade_date_key, trade_date_key)

    all_volumes = []  # 存储每个交易日每个tick的成交量列表
    for trade_date in trade_dates:
        if '-' in trade_date:
            trade_date_key = trade_date.replace('-', '')
        else:
            trade_date_key = trade_date

        tick_data = xtdata.get_market_data(stock_list=[stock_code], period='tick', start_time=trade_date_key, end_time=trade_date_key)

        if isinstance(tick_data[stock_code], np.ndarray) and tick_data[stock_code].dtype.type is np.void:
            df = pd.DataFrame(tick_data[stock_code].tolist(), columns=tick_data[stock_code].dtype.names)
        else:
            continue
            
        df['datetime'] = pd.to_datetime(df['time'], unit='ms').dt.tz_localize('UTC')
        df['datetime'] = df['datetime'].dt.tz_convert('Asia/Shanghai')
        
        # 筛选出 9:30 之后的行
        time_930 = pd.to_datetime('09:30:00').time()
        time_1230 = pd.to_datetime('12:30:00').time()
        filtered_df = df[df['datetime'].dt.time >= time_930]
        filtered_df = filtered_df[filtered_df['datetime'].dt.time < time_1230]
        
        # 获取前收盘成交量
        pre_930_df = df[df['datetime'].dt.time < time_930]
        if not pre_930_df.empty:
            pre_volume = pre_930_df.iloc[-1]['volume']
        else:
            pre_volume = 0
            
        # 计算每个tick的增量成交量
        volumes = []
        have_fei_0 = False

        last_volume = pre_volume
        for index, row in filtered_df.iterrows():
            volume = row['volume']
            delta_volume = volume - last_volume
            if delta_volume < 0:
                delta_volume = 0
            if delta_volume > 0:
                have_fei_0 = True
            volumes.append(delta_volume)
            last_volume = volume
        if not have_fei_0:
            print(f"没有非0 {stock_code} {datekey} {next_trade_day}")
            continue
        if not volumes:
            print(f"没有数据 {stock_code} {datekey} {next_trade_day}")
            continue
        all_volumes.append(volumes)
    
    
    min_length = min(len(volumes) for volumes in all_volumes)
    avg_volumes = []
    for i in range(min_length):
        tick_volumes = [volumes[i] for volumes in all_volumes if i < len(volumes)]
        avg_volume = sum(tick_volumes) / len(tick_volumes)
        avg_volumes.append(avg_volume)

    xtdata.download_history_data(stock_code, 'tick', n_data_key, l_date_key)

    c_open, c_close, n_open, n_close = get_stock_open_close_price(stock_code, n_data_key, l_date_key)
    _,_, n_next_open, n_next_close = get_stock_open_close_price(stock_code, l_date_key, l_next_date_key)


    print(f"获取到{stock_code} {datekey} {next_trade_day} 开盘收盘价: {c_open} {c_close} {n_open} {n_close}")
    if not c_open or not c_close or not n_open or not n_close or c_close <= 0 or n_open <=0 or n_close <= 0 or c_open <= 0:
        logger.error(f"获取开盘收盘价失败 [{stock_code} {datekey}]")
        return {}

    all_tick_data = xtdata.get_market_data(stock_list=[stock_code], period='tick', start_time=n_data_key, end_time=n_data_key)

    # 假设 all_tick_data['000759.SZ'] 是 numpy.void 数组
    if isinstance(all_tick_data[stock_code], np.ndarray) and all_tick_data[stock_code].dtype.type is np.void:
        df = pd.DataFrame(all_tick_data[stock_code].tolist(), columns=all_tick_data[stock_code].dtype.names)
    else:
        raise
    df['datetime'] = pd.to_datetime(df['time'], unit='ms').dt.tz_localize('UTC')
    # 将 UTC 时间转换为上海时间
    df['datetime'] = df['datetime'].dt.tz_convert('Asia/Shanghai')

    # 筛选出 9:30 之后的行
    time_930 = pd.to_datetime('09:30:00').time()
    time_1230 = pd.to_datetime('12:30:00').time()
    filtered_df = df[df['datetime'].dt.time >= time_930]
    filtered_df = filtered_df[filtered_df['datetime'].dt.time < time_1230]
    pre_volume = -1

    pre_930_df = df[df['datetime'].dt.time < time_930]
    if not pre_930_df.empty:
        last_row_pre_930 = pre_930_df.iloc[-1]
        pre_volume = last_row_pre_930.to_dict()['volume']

    else:
        print('last row error.')
        raise
    
    if pre_volume < 0:
        print('pre_volume error.')
        raise

    current_tick_steps = -1

    prices = []
    volumes = []
    datas = []
    base_price = -1
    last_close_price = -1
    last_volume = pre_volume
    for index, row in filtered_df.iterrows():
        current_tick_steps = current_tick_steps + 1
        # if current_tick_steps > 405:
        #     break
        data = row.to_dict()
        timestamp = data['time']
        lastPrice = data['lastPrice']
        open = data['open']
        high = data['high']
        low = data['low']
        lastClose = data['lastClose']
        volume = data['volume']
        amount = data['amount']
        
        if amount <= 0 or volume <= 0:
            print(f"amount <= 0 or volume <= 0. error.")
            continue
        if lastPrice <= 0:
            print(f"lastPrice <= 0. {stock_code} {datekey}")
            continue
        if last_volume == -1:
            volumes.append(volume)
            last_volume = volume
        else:
            delta_volume = volume - last_volume
            if delta_volume < 0:
                print(f"delta_volume < 0. {stock_code} {datekey}")
                continue
            volumes.append(delta_volume)
            last_volume = volume
        
        if current_tick_steps ==0:
            base_price = lastPrice
        if last_close_price < 0:
            last_close_price = lastClose
        prices.append(lastPrice)
        datas.append(data)

    n_prices = []
    n_volumes = []
    n_last_volume = -1
    n_datas = []
    
    all_tick_data_next_day = xtdata.get_market_data(stock_list=[stock_code], period='tick', start_time=l_date_key, end_time=l_date_key)

    # 假设 all_tick_data['000759.SZ'] 是 numpy.void 数组
    if isinstance(all_tick_data_next_day[stock_code], np.ndarray) and all_tick_data_next_day[stock_code].dtype.type is np.void:
        ndf = pd.DataFrame(all_tick_data_next_day[stock_code].tolist(), columns=all_tick_data_next_day[stock_code].dtype.names)
    else:
        raise
    ndf['datetime'] = pd.to_datetime(ndf['time'], unit='ms').dt.tz_localize('UTC')
    # 将 UTC 时间转换为上海时间
    ndf['datetime'] = ndf['datetime'].dt.tz_convert('Asia/Shanghai')

    # 筛选出 9:30 之后的行
    time_930 = pd.to_datetime('09:30:00').time()
    time_1230 = pd.to_datetime('12:30:00').time()
    filtered_df = ndf[ndf['datetime'].dt.time >= time_930]
    filtered_df = filtered_df[filtered_df['datetime'].dt.time < time_1230]
    n_pre_volume = -1

    pre_930_df = ndf[ndf['datetime'].dt.time < time_930]
    if not pre_930_df.empty:
        last_row_pre_930 = pre_930_df.iloc[-1]
        n_pre_volume = last_row_pre_930.to_dict()['volume']

    else:
        print('last row error.')
        raise
    
    if n_pre_volume < 0:
        print('pre_volume error.')
        raise
    n_last_volume = n_pre_volume
    for index, row in filtered_df.iterrows():

        # open = data['open']
        # high = data['high']
        # low = data['low']
        # lastClose = data['lastClose']
        # volume = data['volume']
        # amount = data['amount']
        # pvolume = data['pvolume'] if data['pvolume'] > 0 else 1
        # askPrice = data['askPrice']
        # bidPrice = data['bidPrice']
        # askVol = data['askVol']
        # bidVol = data['bidVol']

        data = row.to_dict()
        data_new = {}
        timestamp = data['time']
        lastPrice = data['lastPrice']
        open = data['open']
        high = data['high']
        low = data['low']
        lastClose = data['lastClose']
        volume = data['volume']
        amount = data['amount']
        askPrice = data['askPrice']
        bidPrice = data['bidPrice']
        askVol = data['askVol']
        bidVol = data['bidVol']

        data_new['lastPrice'] = lastPrice
        data_new['open'] = open
        data_new['high'] = high
        data_new['low'] = low
        data_new['lastClose'] = lastClose
        data_new['volume'] = volume
        data_new['amount'] = amount
        data_new['askPrice'] = askPrice
        data_new['bidPrice'] = bidPrice
        data_new['askVol'] = askVol
        data_new['bidVol'] = bidVol

        if amount <= 0 or volume <= 0:
            print(f"amount <= 0 or volume <= 0. error.")
            continue
        if lastPrice <= 0:
            print(f"lastPrice <= 0. {stock_code} {next_trade_day}")
            continue
        if n_last_volume == -1:
            n_volumes.append(volume)
            n_last_volume = volume
        else:
            delta_volume = volume - n_last_volume
            if delta_volume < 0:
                print(f"delta_volume < 0. {stock_code} {next_trade_day}")
                continue
            n_volumes.append(delta_volume)
            n_last_volume = volume
        
        n_prices.append(lastPrice)
        n_datas.append(data_new)
    
    mkt_datas = get_marketting_datas(stock_code, datekey)

    return {
        'base_price': base_price,
        'prices': prices,
        'open': c_open,
        'close': c_close,
        'volumes': volumes,
        'last_close_price': last_close_price,
        'stock_code': stock_code,
        'n_prices': n_prices,
        'n_volumes': n_volumes,
        'n_open': n_open,
        'n_close': n_close,
        'datekey': datekey,
        'datas': datas,
        'n_datas': n_datas,
        'n_datekey': next_trade_day,
        'n_pre_volume': n_pre_volume,
        'n_mkt_datas': mkt_datas,
        'n_next_open': n_next_open,
        'n_next_close': n_next_close,
        'pre_avg_volumes': avg_volumes,
    }


def build_evaluater_1to2_data_list(result_tuples):
    results = build_all_stock_datas(tuple_list=result_tuples)
    from datetime import datetime
    # 严格模式（可选）
    results.sort(key=lambda x: datetime.strptime(x['datekey'], '%Y-%m-%d'))
    res = []
    i = 1
    for result in results:
        cur_res = {}
        stock_infos = {}
        stock_code = result['stock_code']
        stock_name = ''
        mkt_datas = result['n_mkt_datas']
        tick_datas = result['n_datas']
        order_price = result['base_price']
        stock_infos['order_price'] = order_price
        stock_infos['trade_price'] = order_price
        stock_infos['origin_trade_price'] = order_price
        close = result['close']
        pre_avg_volumes = result['pre_avg_volumes']
        n_next_open = result['n_next_open']
        n_next_close = result['n_next_close']
        n_pre_volume = result['n_pre_volume']
        datekey = result['datekey']

        limit_down_price, limit_up_price = constants.get_limit_price(close)
        stock_infos['limit_up_price'] = limit_up_price
        stock_infos['limit_down_price'] = limit_down_price
        stock_infos['row_id'] = i
        stock_infos['close_price'] = result['n_close']
        if abs(stock_infos['close_price'] - stock_infos['limit_up_price']) < 0.01:
            stock_infos['limit_up'] = 1
        else:
            stock_infos['limit_up'] = 0
        if abs(stock_infos['close_price'] - stock_infos['limit_down_price']) < 0.01:
            stock_infos['limit_down'] = 1
        else:
            stock_infos['limit_down'] = 0
        
        stock_infos['pre_avg_volumes'] = pre_avg_volumes
        stock_infos['n_next_open'] = n_next_open
        stock_infos['n_next_close'] = n_next_close
        stock_infos['n_pre_volume'] = n_pre_volume
        stock_infos['datekey'] = datekey
        n_open = result['n_open']
        if n_open / order_price > 1:
            monitor_type = 1
        else:
            monitor_type = 3
        stock_infos['monitor_type'] = monitor_type
        stock_infos['tick_datas'] = tick_datas
        stock_infos['n_open'] = n_open

        cur_res['stock_code'] = stock_code
        cur_res['stock_name'] = stock_name
        cur_res['stock_infos'] = stock_infos
        cur_res['mkt_datas'] = mkt_datas
        cur_res['datekey'] = datekey

        res.append(cur_res)
        i += 1
    return res
  # 确保导入Timestamp

def build_evaluater_1to2_data_list_from_file(nums = 3):
    import pandas as pd
    res_list = []
    # 读取CSV文件
    save_path1 = r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_d5.csv'
    save_path2 = r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_dd5.csv'
    # save_path3 = r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_z1.csv'
    # for save_path in [save_path1, save_path2, save_path3]:
    for save_path in [save_path1, save_path2]:
        loaded_df = pd.read_csv(save_path)
        result_tuples = list(zip(loaded_df['date_key'], loaded_df['stock_code']))
        result_tuples.sort(key=lambda x: pd.to_datetime(x[0], format='%Y-%m-%d'))
        result_tuples = result_tuples[-nums:]
        print(result_tuples)

        res = build_evaluater_1to2_data_list(result_tuples)
        res_list.append(res)
    return res_list


def serialize(obj):
    """自定义JSON序列化器，处理Timestamp等特殊类型"""
    if isinstance(obj, Timestamp):
        # 转换为'yyyy-MM-dd HH:mm:ss'格式字符串
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    # 可扩展处理其他类型（如numpy数值类型）
    # elif isinstance(obj, np.ndarray):
    #     return obj.tolist()
    raise TypeError(f"不支持序列化类型: {type(obj)}")


if __name__ == "__main__":
    res = build_evaluater_1to2_data_list_from_file(5)
    def serialize(obj):
        # 处理列表截断（只保留前100项）
        if isinstance(obj, list):
            return obj[:100]  # 截断列表至前100个元素
        # 保留原有的datetime处理逻辑
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        # 其他类型处理（如有需要）
        raise TypeError(f"Type {type(obj)} not serializable")
    file_path = r'd:\workspace\TradeX\notebook\new_strategy_eval\result_dict.json'

    # 保存字典到JSON文件（格式化输出）
    with open(file_path, 'a', encoding='utf-8') as f:
        for item in res[0]:
            json.dump(item, f, ensure_ascii=False, indent=2, default=serialize)
    print(len(res))