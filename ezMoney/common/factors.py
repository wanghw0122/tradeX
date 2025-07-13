from xtquant import xtdata
import time
from date_utils import date
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from scipy.stats import linregress
import numpy as np
# 创建公共线程池
pool = ThreadPoolExecutor(max_workers=4) 


# 收益率因子
def get_return_n_days(stock, n, start_date="", end_date=""):
    """
    获取股票过去n天的收益率
    """
    if '-' in start_date:
        start_date = start_date.replace('-', '')
    if '-' in end_date:
        end_date = end_date.replace('-', '')
    cur_day = date.get_current_date()

    if not start_date and not end_date:
       pass
       

    # 获取股票过去n天的收盘价
    # close_price = xtdata.get_bar(stock, start_date, end_date, '1d')['close']


def convert_dict(ac):
    result = {}
    # 排除 'time' 键
    keys_to_process = [key for key in ac.keys()]
    for key in keys_to_process:
        df = ac[key]
        for stock_code in df.index:
            if stock_code not in result:
                result[stock_code] = pd.DataFrame(index=df.columns).sort_index(ascending=False)
            result[stock_code][key] = df.loc[stock_code]
    return result

## 获取日线级别数据, datekey= 2023-01-01


def get_n_days_data(stock_code, datekey, days = 7):

    import datetime
    """
    判断是否前一天一字涨停（包含 T 型板、高开封板且低成交量），昨天放量断板的股票
    :param df: 股票数据 DataFrame
    :return: 是否满足条件
    """
    date_list = date.get_trade_dates_by_end(datekey, 2 * days + 10)
    if datekey in date_list:
        date_list.remove(datekey)

    date_objects = [datetime.datetime.strptime(date_str, '%Y-%m-%d') for date_str in date_list]
    # 按日期降序排序
    date_objects.sort(reverse=True)
    # 将排序后的 datetime 对象转回字符串
    date_list = [date_obj.strftime('%Y-%m-%d') for date_obj in date_objects]

    s_date = date_list[days * 2].replace('-', '')
    e_date = date_list[0].replace('-', '')

    xtdata.download_history_data(stock_code, '1d', s_date, e_date)


    ac = xtdata.get_market_data([],[stock_code],period="1d",start_time = s_date, end_time = e_date)
    df = convert_dict(ac)[stock_code]
    valid_days = df[df['suspendFlag'] == 0].head(days)
    if len(valid_days) < 2:
        print(f"no df data. {stock_code} - {datekey}")
        return None
    
    print(f'{stock_code} - {valid_days}')

    return valid_days


def get_n_days_data_batch(stock_codes, datekey, days = 7):
    futures = []
    for stock_code in stock_codes:
        # 提交任务到线程池
        future = pool.submit(get_n_days_data, stock_code, datekey, days)
        futures.append(future)
    
    # 获取任务结果
    results = [future.result() for future in futures]
    return results


def calculate_technical_factors(df, window=10):
    """
    计算技术分析因子
    :param df: 包含原始数据的DataFrame
    :param window: 分析窗口大小
    :return: 包含技术因子的DataFrame
    """
    # 基础计算
    df['returns'] = df['close'].pct_change()
    df['prev_close'] = df['close'].shift(1)
    
    # 1. 动量类因子
    # 价格斜率因子 (5日)
    df['price_slope_5'] = df['close'].rolling(window=5).apply(
        lambda x: linregress(np.arange(len(x)), x).slope, raw=True)
    
    # 相对强弱因子 (10日)
    up_days = df['close'].diff().apply(lambda x: x if x > 0 else 0).rolling(window=window).sum()
    down_days = df['close'].diff().apply(lambda x: -x if x < 0 else 0).rolling(window=window).sum()
    df['RSI'] = 100 - (100 / (1 + (up_days / down_days)))
    
    # 2. 成交量类因子
    # 量价背离因子
    df['volume_ma_5'] = df['volume'].rolling(window=5).mean()
    df['price_ma_5'] = df['close'].rolling(window=5).mean()
    df['volume_price_divergence'] = df['volume_ma_5'] / df['price_ma_5']
    
    # 量能聚集因子 (10日)
    df['volatility'] = df['high'] - df['low']
    df['volume_cluster'] = df['volume'].rolling(window=window).std() / df['volatility'].rolling(window=window).mean()
    
    # 3. 价格位置因子
    # 价格通道位置 (10日)
    df['high_10'] = df['high'].rolling(window=window).max()
    df['low_10'] = df['low'].rolling(window=window).min()
    df['price_position'] = (df['close'] - df['low_10']) / (df['high_10'] - df['low_10'])
    
    # 均线排列因子 (5日)
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma_arrangement'] = (df['ma5'] > df['ma10']).astype(int)
    
    # 4. 波动率因子
    # 真实波幅 (ATR)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['ATR_5'] = df['true_range'].rolling(window=5).mean()
    
    # 5. 特殊形态因子
    # 炸板识别因子
    df['is_limit_up'] = (df['high'] == df['low']) & (df['close'] > df['prev_close'] * 1.095)
    df['limit_up_open'] = df['is_limit_up'].shift(1)
    df['volume_change'] = df['volume'] / df['volume'].shift(1)
    df['is_blow_up'] = (df['limit_up_open'] & 
                       (df['close'] < df['open'] * 0.97) & 
                       (df['volume_change'] > 1.8))
    
    # 长上影线识别 (射击之星)
    body_size = abs(df['close'] - df['open'])
    upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
    df['is_shooting_star'] = (upper_shadow > body_size * 1.5) & (df['close'] < df['open'])
    
    # 6. 趋势强度因子
    # ADI 趋势强度
    df['cmf'] = ((2*df['close'] - df['low'] - df['high']) / 
                (df['high'] - df['low'])) * df['volume']
    df['ADI_10'] = df['cmf'].rolling(window=10).sum()
    
    # 7. 量价协同因子
    # OBV 能量潮
    df['obv'] = np.where(df['close'] > df['prev_close'], 
                        df['volume'], 
                        np.where(df['close'] < df['prev_close'], -df['volume'], 0)).cumsum()
    
    return df



def my_download(stock_list:list,period:str,start_date = '', end_date = ''):
    '''
    用于显示下载进度
    '''
    import string
    
    if [i for i in ["d","w","mon","q","y",] if i in period]:
        period = "1d"
    elif "m" in period:
        numb = period.translate(str.maketrans("", "", string.ascii_letters))
        if int(numb) < 5:
            period = "1m"
        else:
            period = "5m"
    elif "tick" == period:
        pass
    else:
        raise KeyboardInterrupt("周期传入错误")


    n = 1
    num = len(stock_list)
    for i in stock_list:
        print(f"当前正在下载 {period} {n}/{num}")
        
        xtdata.download_history_data(i,period,start_date, end_date)
        n += 1
    print("下载任务结束")


def do_subscribe_quote(stock_list:list, period:str):
  for i in stock_list:
    xtdata.subscribe_quote(i,period = period)
  time.sleep(1) # 等待订阅完成

if __name__ == "__main__":

  start_date = '20250401'# 格式"YYYYMMDD"，开始下载的日期，date = ""时全量下载
  end_date = "" 
  period = "1d" 

  need_download = 1  # 取数据是空值时，将need_download赋值为1，确保正确下载了历史数据
  
  code_list = ["000001.SZ", "600519.SH"] # 股票列表

  if need_download: # 判断要不要下载数据, gmd系列函数都是从本地读取历史数据,从服务器订阅获取最新数据
    my_download(code_list, period, start_date, end_date)
  
  ############ 仅获取历史行情 #####################
  count = -1 # 设置count参数，使gmd_ex返回全部数据
  data1 = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_date, end_time = end_date)

  ############ 仅获取最新行情 #####################
  do_subscribe_quote(code_list,period)# 设置订阅参数，使gmd_ex取到最新行情
  count = 1 # 设置count参数，使gmd_ex仅返回最新行情数据
  data2 = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_date, end_time = end_date, count = 1) # count 设置为1，使返回值只包含最新行情

  ############ 获取历史行情+最新行情 #####################
  do_subscribe_quote(code_list,period) # 设置订阅参数，使gmd_ex取到最新行情
  count = -1 # 设置count参数，使gmd_ex返回全部数据
  data3 = xtdata.get_market_data_ex([],code_list,period = period, start_time = start_date, end_time = end_date, count = -1) # count 设置为1，使返回值只包含最新行情


  print(data1[code_list[0]].tail())# 行情数据查看
  print(data2[code_list[0]].tail())
  print(data3[code_list[0]].tail())




