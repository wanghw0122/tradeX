from common import constants
from sqlite_processor.mysqlite import SQLiteManager
import threading
import queue
from date_utils import date
import datetime
from logger import strategy_logger as logger

def calculate_seconds_difference(specified_time):
    current_time = datetime.datetime.now().timestamp()
    time_difference =  current_time - (specified_time / 1000)
    return time_difference


monitor_table = 'monitor_data'
monitor_config_table = "strategy_monitor_config"


from collections import deque

class SmoothFilter:
    def __init__(self, window_size=10):
        self.window = deque(maxlen=window_size)  # 滑动窗口
        self.smoothed_value = 0
        
    def update(self, new_value):
        self.window.append(new_value)
        self.smoothed_value = sum(self.window)/len(self.window)
        return self.smoothed_value

class StockMonitor(object):
    def __init__(self, stock_code, stock_name, qmt_trader = None, mkt_datas = None):
        # self.config = {}
        self.monitor_configs = {}
        # self.config['step_tick_gap'] = 5
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.mkt_datas = mkt_datas
        if mkt_datas and 'ma5' in mkt_datas:
            self.ma5 = mkt_datas['ma5']
        else:
            self.ma5 = 0
        if mkt_datas and'ma10' in mkt_datas:
            self.ma10 = mkt_datas['ma10']
        else:
            self.ma10 = 0
        if mkt_datas and'ma20' in mkt_datas:
            self.ma20 = mkt_datas['ma20']
        else:
            self.ma20 = 0
        if mkt_datas and'ma30' in mkt_datas:
            self.ma30 = mkt_datas['ma30']
        else:
            self.ma30 = 0
        if mkt_datas and'ma60' in mkt_datas:
            self.ma60 = mkt_datas['ma60']
        else:
            self.ma60 = 0
        if qmt_trader != None:
            self.qmt_trader = qmt_trader
        self.open_status = -1
        self.end = False
        # 均价
        self.avg_price = 0
        # 当前价
        self.current_price = 0
        # 平滑当前价
        self.smooth_current_price = 0
        # 平滑过滤器
        self.smooth_price_filter = SmoothFilter(window_size=3)

        # 涨停最大封单量
        self.max_limit_up_vol = -1
        # 开盘价
        self.open_price = 0
        # 昨天收盘价
        self.last_close_price = 0
        # 当前步数
        self.current_tick_steps = -1
        # 当前天内涨幅
        self.current_open_increase = 0
        # 当天涨幅
        self.current_increase = 0
        # 当天最高价
        self.current_max_price = 0
        # 当天最低价
        self.current_min_price = 0
        # 当天天内最高涨幅
        self.current_max_open_increase = -1
        # 当天天内最低涨幅
        self.current_min_open_increase = -1
        # 当天最高涨幅
        self.current_max_increase = -1
        # 当天最低涨幅
        self.current_min_increase = -1
        # 涨停标记
        self.limit_up_status = False
        # 跌停标记
        self.limit_down_status = False
        # 当天涨停价
        self.limit_up_price = -1
        # 当天跌停价
        self.limit_down_price = -1

        self.limit_up_tick_times = -1
        # 已经卖出rowid
        self.selled_row_ids = []
        # 准备卖出的rowid
        self.to_sell_row_ids = []
        # 剩余未卖出
        self.left_row_ids = []

        self.bq = queue.Queue()
        self.row_id_to_monitor_data = {}

        self.monitor_type_to_row_ids = {}

        self.running_monitor_status = {}
        self.running_monitor_stock_status = {}

        self.running_monitor_down_status = {}

        self.running_monitor_observe_steps = {}

        with SQLiteManager(constants.db_path) as db:
            self.query_data_lists = db.query_data_dict(monitor_table, condition_dict= {'date_key': date.get_current_date(), 'stock_code': stock_code, 'monitor_status': 1})
            if not self.query_data_lists:
                logger.error(f"query_data_lists null. {stock_code}-{stock_name}")
            for query_data in self.query_data_lists:
                row_id = query_data['id']
                strategy_name = query_data['strategy_name']
                sub_strategy_name = query_data['sub_strategy_name']
                if row_id not in self.left_row_ids:
                    self.left_row_ids.append(row_id)
                if strategy_name not in self.running_monitor_status:
                    self.running_monitor_status[strategy_name] = constants.StockStatus.COLD_START
                if strategy_name not in self.running_monitor_stock_status:
                    self.running_monitor_stock_status[strategy_name] = constants.StockStatus.UNKNOWN
                if strategy_name not in self.running_monitor_observe_steps:
                    self.running_monitor_observe_steps[strategy_name] = 0
                if strategy_name not in self.running_monitor_down_status:
                    self.running_monitor_down_status[strategy_name] = False
                self.row_id_to_monitor_data[row_id] = query_data
                monitor_type = query_data['monitor_type']
                monitor_config = db.query_data_dict(monitor_config_table, condition_dict= {'strategy_name': strategy_name})
                default_monitor_config = db.query_data_dict(monitor_config_table, condition_dict= {'strategy_name': 'default'})
                if not monitor_config and not default_monitor_config:
                    logger.error(f"monitor_config null. {strategy_name}")
                    continue
                if not monitor_config:
                    monitor_config = default_monitor_config
                monitor_config = monitor_config[0]
                self.monitor_configs[strategy_name] = monitor_config
                # if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                #     pass
                if monitor_type not in self.monitor_type_to_row_ids:
                    self.monitor_type_to_row_ids[monitor_type] = [row_id]
                else:
                    self.monitor_type_to_row_ids[monitor_type].append(row_id)
        # 打印日志
        logger.info(f"已卖出的 rowid 列表: {self.selled_row_ids}")
        logger.info(f"准备卖出的 rowid 列表: {self.to_sell_row_ids}")
        logger.info(f"剩余未卖出的 rowid 列表: {self.left_row_ids}")
        logger.info(f"队列 bq 当前大小: {self.bq.qsize()}")
        logger.info(f"row_id 到监控数据的映射: {self.row_id_to_monitor_data}")
        logger.info(f"监控类型到 row_id 列表的映射: {self.monitor_type_to_row_ids}")
        logger.info(f"运行中的监控状态: {self.running_monitor_status}")
        logger.info(f"运行中的股票监控状态: {self.running_monitor_stock_status}")
        logger.info(f"运行中的下跌监控状态: {self.running_monitor_down_status}")
        logger.info(f"运行中的监控观察步数: {self.running_monitor_observe_steps}")

        self.start_monitor()
        

        # self.config = config
        # self.db_name = config['db_name']
        # self.table_name = config['table_name']
    def start_monitor(self):
        logger.info(f"start monitor {self.stock_code} {self.stock_name}")
        self.thread = threading.Thread(target=self.monitor)
        self.thread.start()
        return self.thread
    

    def stop_monitor(self):
        logger.info(f"stop monitor {self.stock_code} {self.stock_name}")
        self.thread.join()
    
    def monitor(self):
        while True:
            if not self.left_row_ids:
                logger.error(f"{self.stock_code}-{self.stock_name} 没有需要监控的卖出任务")
                self.end = True
                break
            data = self.bq.get()
            if data is None:
                continue
            # m = {}
            time = data['time']
            diff = calculate_seconds_difference(time)
            if diff > 10:
                logger.error(f"time diff > 10s. {diff} {time} {self.stock_code} {self.stock_name}")
                continue

            lastPrice = data['lastPrice']
            open = data['open']
            high = data['high']
            low = data['low']
            lastClose = data['lastClose']
            volume = data['volume']
            amount = data['amount']
            pvolume = data['pvolume'] if data['pvolume'] > 0 else 1
            askPrice = data['askPrice']
            bidPrice = data['bidPrice']
            askVol = data['askVol']
            bidVol = data['bidVol']
            if self.open_status == -1:
                self.open_status = constants.OpenStatus.DOWN_OPEN if open <= lastClose else constants.OpenStatus.UP_OPEN
            if amount <= 0 or volume <= 0:
                logger.error(f"amount <= 0. {amount} {time} {self.stock_code} {self.stock_name}")
                continue
            if lastPrice <= 0:
                logger.error(f"lastPrice <= 0. {lastPrice} {time} {self.stock_code} {self.stock_name}")
                continue
            
            # 均价
            self.avg_price = amount / volume / 100
            # 当前价
            self.current_price = lastPrice
            self.smooth_current_price = self.smooth_price_filter.update(self.current_price)
            # 开盘价
            self.open_price = open
            # 昨天收盘价
            self.last_close_price = lastClose
            # 当前步数
            self.current_tick_steps = self.current_tick_steps + 1
            # 当前天内涨幅
            self.current_open_increase = (self.current_price - self.open_price) / self.open_price
            # 当天涨幅
            self.current_increase = (self.current_price - self.last_close_price) / self.last_close_price
            # 当天最高价
            self.current_max_price = max(self.current_max_price, high)
            # 当天最低价
            self.current_min_price = min(self.current_min_price, low)
            # 当天天内最高涨幅
            self.current_max_open_increase = (self.current_max_price - self.open_price) / self.open_price
            # 当天天内最低涨幅
            self.current_min_open_increase = (self.current_min_price - self.open_price) / self.open_price
            # 当天最高涨幅
            self.current_max_increase = (self.current_max_price - self.last_close_price) / self.last_close_price
            # 当天最低涨幅
            self.current_min_increase = (self.current_min_price - self.last_close_price) / self.last_close_price

            logger.info(
                f"股票代码： {self.stock_code}, 股票名称： {self.stock_name}, "
                f"均价: {self.avg_price:.2f}, 当前价: {self.current_price:.2f}, 开盘价: {self.open_price:.2f}, "
                f"昨天收盘价: {self.last_close_price:.2f}, 当前步数: {self.current_tick_steps}, "
                f"当前天内涨幅: {self.current_open_increase:.2%}, 当天涨幅: {self.current_increase:.2%}, "
                f"当天最高价: {self.current_max_price:.2f}, 当天最低价: {self.current_min_price:.2f}, "
                f"当天天内最高涨幅: {self.current_max_open_increase:.2%}, 当天天内最低涨幅: {self.current_min_open_increase:.2%}, "
                f"当天最高涨幅: {self.current_max_increase:.2%}, 当天最低涨幅: {self.current_min_increase:.2%}"
            )

            if self.limit_up_price < 0 or self.limit_down_price < 0:
                limit_down_price_0, limit_up_price_0 = constants.get_limit_price(self.last_close_price, stock_code=self.stock_code)
                self.limit_up_price = limit_up_price_0
                self.limit_down_price = limit_down_price_0

            if self.limit_up_price > 0 and abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
                if not bidPrice or not bidVol:
                    self.sell_all(price = self.current_price)
                    continue
                self.max_limit_up_vol = max(self.max_limit_up_vol, bidVol[0])

                buy1_price = bidPrice[0]
                buy1_vol = bidVol[0]
                if abs(buy1_price - self.limit_up_price) >= 0.01:
                    if buy1_price > 0:
                        self.sell_all(price = buy1_price)
                    else:
                        self.sell_all(price = self.current_price)
                    continue
                # 封单金额过小 卖
                if buy1_price * buy1_vol * 100 < 35000000 and buy1_vol / self.max_limit_up_vol < 0.5:
                    logger.info(f"封单金额过小，卖出 {self.stock_code} {self.stock_name}")
                    if buy1_price > 0:
                        self.sell_all(price = buy1_price)
                    else:
                        self.sell_all(price = self.current_price)
                    continue

                if self.limit_up_status:
                    self.limit_up_tick_times = self.limit_up_tick_times + 1
                    if self.limit_up_tick_times > 3:
                        if not bidPrice or not bidVol:
                            self.sell_all(price = self.current_price)
                            continue
                        buy1_price = bidPrice[0]
                        buy1_vol = bidVol[0]
                        if abs(buy1_price - self.limit_up_price) >= 0.01:
                            if buy1_price > 0:
                                self.sell_all(price = buy1_price)
                            else:
                                self.sell_all(price = self.current_price)
                            continue
                        # 封单金额过小 卖
                        if buy1_price * buy1_vol * 100 < 8000000:
                            logger.info(f"封单金额过小，卖出 {self.stock_code} {self.stock_name}")
                            if buy1_price > 0:
                                self.sell_all(price = buy1_price)
                            else:
                                self.sell_all(price = self.current_price)
                            continue
                else:
                    self.limit_up_tick_times = 0
                    self.limit_up_status = True

            elif self.limit_up_price > 0 and abs(self.smooth_current_price - self.limit_up_price) >= 0.0033:
                self.max_limit_up_vol = -1
                self.limit_up_tick_times = -1
                if self.limit_up_status:
                    # 涨停炸板卖
                    logger.info(f"炸板了，卖出 {self.stock_code} {self.stock_name}")
                    if not bidPrice or not bidVol:
                        self.sell_all(price = self.current_price)
                    else:
                        buy1_price = bidPrice[0]
                        buy1_vol = bidVol[0]
                        if len(bidPrice) > 1 and len(bidVol) > 1:
                            buy2_price = bidPrice[1]
                            buy2_vol = bidVol[1]
                        else:
                            buy2_price = 0
                            buy2_vol = 0
                        if buy1_price * buy1_vol * 100 < 500000:
                            if buy2_price > 0:
                                self.sell_all(price = buy2_price)
                            else:
                                if buy1_price > 0:
                                    self.sell_all(price = buy1_price)
                                else:
                                    self.sell_all(price = self.current_price)
                        else:
                            if buy1_price > 0:
                                self.sell_all(price = buy1_price)
                            else:
                                self.sell_all(price = self.current_price)
                    self.limit_up_status = False
                    continue
                self.limit_up_status = False
            else:
                self.limit_up_status = False
                self.max_limit_up_vol = -1
            if self.limit_down_price > 0 and abs(self.current_price - self.limit_down_price) < 0.01:
                self.limit_down_status = True
            else:
                self.limit_down_status = False
            
            if self.limit_up_status:
                continue

            current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
            
            for monitor_type, row_ids in self.monitor_type_to_row_ids.items():
                if not row_ids:
                    continue
                if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']
                        if strategy_name not in self.monitor_configs:
                            logger.error(f"策略{strategy_name} 无配置 跳过")
                            if row_id not in self.selled_row_ids:
                                self.selled_row_ids.append(row_id)
                            if row_id in self.left_row_ids:
                                self.left_row_ids.remove(row_id)
                            continue
                        monitor_config = self.monitor_configs[strategy_name]
                        # tick的gap间隔
                        per_step_tick_gap = monitor_config['per_step_tick_gap']
                        # 等待冷启动次数
                        cold_start_steps = monitor_config['cold_start_steps']
                        # 最大观察的tick数量
                        max_abserve_tick_steps = monitor_config['max_abserve_tick_steps']
                        # 跌落均线下观察的tick数量
                        max_abserce_avg_price_down_steps = monitor_config['max_abserce_avg_price_down_steps']
                        # 止盈的开盘最大下跌
                        stop_profit_open_hc_pct = monitor_config['stop_profit_open_hc_pct']
                        # 止盈的最小止盈点
                        stop_profit_pct = monitor_config['stop_profit_pct']
                        # 动态回撤的系数
                        dynamic_hc_stop_profit_thres = monitor_config['dynamic_hc_stop_profit_thres']
                        # 静态回撤的幅度
                        static_hc_stop_profit_pct = monitor_config['static_hc_stop_profit_pct']
                        # 前一天收盘价的水下容忍比例
                        last_close_price_hc_pct = monitor_config['last_close_price_hc_pct']

                        # 动态止盈线
                        dynamic_zs_line = -1
                        # 静态止盈线
                        static_zs_line = -1

                        if dynamic_hc_stop_profit_thres > 0:
                            a = ((10 - self.current_max_increase * 100) * dynamic_hc_stop_profit_thres) / 100
                            a = max(a, 0.005)
                            a = min(a, 0.05)
                            dynamic_zs_line = (1 - a) * self.current_max_price
                            dynamic_zs_line = max(dynamic_zs_line, limit_down_price)
                            dynamic_zs_line = min(dynamic_zs_line, limit_up_price)
                            if abs(dynamic_zs_line - self.current_max_increase) < 0.01:
                                dynamic_zs_line = self.current_max_increase - 0.01
                            
                        if static_hc_stop_profit_pct > 0 and static_hc_stop_profit_pct < 1:
                            static_zs_line = self.current_max_price * (1 - static_hc_stop_profit_pct)
                            static_zs_line = max(static_zs_line, limit_down_price)
                            static_zs_line = min(static_zs_line, limit_up_price)


                        open_hc_line = self.open_price * (1 + stop_profit_open_hc_pct)
                        stop_profit_line = trade_price * (1 + stop_profit_pct)

                        zs_line = max(open_hc_line, stop_profit_line)

                        logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 动态止盈线: {dynamic_zs_line:.2f}, 静态止盈线: {static_zs_line:.2f}, 止损线: {zs_line:.2f}")

                        if self.current_tick_steps < cold_start_steps:
                            continue
                        elif self.current_tick_steps == cold_start_steps:
                            # if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                            #     self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                
                            # elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                            #     self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                
                            # elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                            #     self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                
                            # elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                            #     self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                            
                            # if self.current_price <= self.avg_price:
                            #     self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                            # else:
                            #     self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                            
                            # self.running_monitor_down_status[strategy_name] = False
                            # self.running_monitor_observe_steps[strategy_name] = 0

                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")

                            if self.current_price <= self.avg_price:
                                self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")
                            else:
                                self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")

                            self.running_monitor_down_status[strategy_name] = False
                            self.running_monitor_observe_steps[strategy_name] = 0
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_down_status 更新为 {self.running_monitor_down_status[strategy_name]}")
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_observe_steps 更新为 {self.running_monitor_observe_steps[strategy_name]}")

                        elif self.current_tick_steps > cold_start_steps:
                            if self.current_tick_steps % per_step_tick_gap == 0:
                                # 低开低走
                                if self.running_monitor_status[strategy_name] == constants.StockStatus.DOWN_LOW_AVG_DOWN:
                                    if self.smooth_current_price < zs_line and self.smooth_current_price <= self.avg_price:
                                        if self.limit_down_status:
                                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                                        else:
                                            if self.current_tick_steps < max_abserve_tick_steps:
                                                # 5min内增加一定的容忍性
                                                if self.smooth_current_price < self.ma5:
                                                    
                                                    logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                            else:
                                                logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                    # 均线下
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        
                                        if self.current_price <= self.avg_price:
                                            if self.running_monitor_down_status[strategy_name]:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                    if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            pass
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.smooth_current_price < zs_line and self.smooth_current_price <= self.avg_price:
                                            if self.limit_down_status:
                                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                                            else:
                                                if self.current_tick_steps < max_abserve_tick_steps:
                                                    # 5min内增加一定的容忍性
                                                    if self.smooth_current_price < self.ma5:
                                                        
                                                        logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                                else:
                                                    logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0

                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.DOWN_HIGH_AVG_UP:
                                    if self.smooth_current_price < zs_line and self.smooth_current_price <= self.avg_price:
                                        if self.limit_down_status:
                                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                                        else:
                                            if self.current_tick_steps < max_abserve_tick_steps:
                                                # 5min内增加一定的容忍性
                                                if self.smooth_current_price < self.ma5:
                                                    
                                                    logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                            else:
                                                logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <= self.avg_price:
                                            if self.running_monitor_down_status[strategy_name]:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                    if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.UP_LOW_AVG_DOWN:
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.smooth_current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                            #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                            # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                            #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.smooth_current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                
                                                if self.running_monitor_down_status[strategy_name]:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                        if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                            logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                            self.add_to_sell(row_id=row_id)
                                                            continue
                                                else:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue

                                            else:
                                                if self.current_price <= self.open_price * (1 + last_close_price_hc_pct):
                                                    logger.info(f"跌破开盘价卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.UP_HIGH_AVG_UP:
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.smooth_current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                            #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                            # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                            #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.smooth_current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                
                                                if self.running_monitor_down_status[strategy_name]:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                        if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                            logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                            self.add_to_sell(row_id=row_id)
                                                            continue
                                                else:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue

                                            else:
                                                if self.current_price <= self.open_price * (1 + last_close_price_hc_pct):
                                                    logger.info(f"跌破均价线，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                            else:
                                now = datetime.datetime.now().time()
                                target_time = datetime.time(11, 25)
                                if now > target_time:
                                    logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 超过最大时间卖出")
                                    self.add_to_sell(row_id=row_id)
                    
                elif monitor_type == constants.STOP_LOSS_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']

                        if strategy_name not in self.monitor_configs:
                            logger.error(f"策略{strategy_name} 无配置 跳过")
                            if row_id not in self.selled_row_ids:
                                self.selled_row_ids.append(row_id)
                            if row_id in self.left_row_ids:
                                self.left_row_ids.remove(row_id)
                            continue
                        monitor_config = self.monitor_configs[strategy_name]
                        per_step_tick_gap = monitor_config['per_step_tick_gap']
                        cold_start_steps = monitor_config['cold_start_steps']
                        max_abserve_tick_steps = monitor_config['max_abserve_tick_steps']
                        max_abserce_avg_price_down_steps = monitor_config['max_abserce_avg_price_down_steps']
                        
                        dynamic_hc_stop_profit_thres = monitor_config['dynamic_hc_stop_profit_thres']
                        static_hc_stop_profit_pct = monitor_config['static_hc_stop_profit_pct']
                        last_close_price_hc_pct = monitor_config['last_close_price_hc_pct']
                        dynamic_zs_line = -1
                        static_zs_line = -1

                        if dynamic_hc_stop_profit_thres > 0:
                            a = ((10 - self.current_max_increase * 100) * dynamic_hc_stop_profit_thres) / 100
                            a = max(a, 0.005)
                            a = min(a, 0.05)
                            dynamic_zs_line = (1 - a) * self.current_max_price
                            dynamic_zs_line = max(dynamic_zs_line, limit_down_price)
                            dynamic_zs_line = min(dynamic_zs_line, limit_up_price)
                            if abs(dynamic_zs_line - self.current_max_increase) < 0.01:
                                dynamic_zs_line = self.current_max_increase - 0.01
                            
                        if static_hc_stop_profit_pct > 0 and static_hc_stop_profit_pct < 1:
                            static_zs_line = self.current_max_price * (1 - static_hc_stop_profit_pct)
                            static_zs_line = max(static_zs_line, limit_down_price)
                            static_zs_line = min(static_zs_line, limit_up_price)

                        logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 动态止盈线: {dynamic_zs_line:.2f}, 静态止盈线: {static_zs_line:.2f}")

                        if self.current_tick_steps < cold_start_steps:
                            continue
                        elif self.current_tick_steps == cold_start_steps:
                            
                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")

                            if self.current_price <= self.avg_price:
                                self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")
                            else:
                                self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[strategy_name]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")

                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                if not self.limit_down_status:
                                    # 直接割
                                    logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                    self.add_to_sell(row_id=row_id)
                                    continue

                            self.running_monitor_down_status[strategy_name] = False
                            self.running_monitor_observe_steps[strategy_name] = 0
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_down_status 更新为 {self.running_monitor_down_status[strategy_name]}")
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_observe_steps 更新为 {self.running_monitor_observe_steps[strategy_name]}")
                            
                        elif self.current_tick_steps > cold_start_steps:
                            if self.current_tick_steps % per_step_tick_gap == 0:
                                if self.running_monitor_status[strategy_name] == constants.StockStatus.DOWN_LOW_AVG_DOWN:
                                    if self.smooth_current_price <= self.open_price:
                                        if not self.limit_down_status:
                                            # 直接割
                                            logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            
                                            if self.running_monitor_down_status[strategy_name]:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                    if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                            
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        else:
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0

                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.DOWN_HIGH_AVG_UP:
                                    if self.smooth_current_price <= self.open_price:
                                         if not self.limit_down_status:
                                            # 直接割
                                            logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        else:
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <= self.avg_price:
                                            if self.running_monitor_down_status[strategy_name]:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                    if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP

                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        else:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.UP_LOW_AVG_DOWN:
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.smooth_current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                            #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                            # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                            #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                
                                                if self.running_monitor_down_status[strategy_name]:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                        if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                            logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                            self.add_to_sell(row_id=row_id)
                                                            continue
                                                else:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_price <= self.open_price * (1 + last_close_price_hc_pct):
                                                    logger.info(f"跌破开盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                elif self.running_monitor_status[strategy_name] == constants.StockStatus.UP_HIGH_AVG_UP:
                                    
                                    if self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_UP:
                                        if self.smooth_current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                            #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                            # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                            #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                            #     self.sell()
                                            #     continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[strategy_name] = True
                                            self.running_monitor_observe_steps[strategy_name] = 0
                                    elif self.running_monitor_stock_status[strategy_name] == constants.StockStatus.AVG_DOWN:
                                        if self.current_price <=  self.last_close_price * (1 + last_close_price_hc_pct):
                                            logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                
                                                if self.running_monitor_down_status[strategy_name]:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        self.running_monitor_observe_steps[strategy_name] = self.running_monitor_observe_steps[strategy_name] + 1
                                                        if self.running_monitor_observe_steps[strategy_name] >= max_abserce_avg_price_down_steps:
                                                            logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                            self.add_to_sell(row_id=row_id)
                                                            continue
                                                else:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_price <= self.open_price * (1 + last_close_price_hc_pct):
                                                    logger.info(f"跌破开盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                            
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                                            self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                                        
                            else:
                                now = datetime.datetime.now().time()
                                target_time = datetime.time(11, 25)
                                if now > target_time:
                                    logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 超过最大时间卖出")
                                    self.add_to_sell(row_id=row_id)
                                pass
                elif monitor_type ==  constants.LAST_TRADE_DAY_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']
                        if strategy_name not in self.monitor_configs:
                            logger.error(f"策略{strategy_name} 无配置 跳过")
                            if row_id not in self.selled_row_ids:
                                self.selled_row_ids.append(row_id)
                            if row_id in self.left_row_ids:
                                self.left_row_ids.remove(row_id)
                            continue
                        monitor_config = self.monitor_configs[strategy_name]
                        per_step_tick_gap = monitor_config['per_step_tick_gap']
                        cold_start_steps = monitor_config['cold_start_steps']
                        max_abserve_tick_steps = monitor_config['max_abserve_tick_steps']
                        max_abserce_avg_price_down_steps = monitor_config['max_abserce_avg_price_down_steps']
                        last_day_sell_thres = monitor_config['last_day_sell_thres']
                        max_thres_line = self.current_max_price * (1 - 0.005)
                        if self.current_increase > last_day_sell_thres and self.current_price < max_thres_line:
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 回撤卖出")
                            self.add_to_sell(row_id=row_id)
                            continue
                        # now = datetime.datetime.now().time()
                        # target_time = datetime.time(11, 25)
                        # if now > target_time:
                        #     logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 超过最大时间卖出")
                        #     self.add_to_sell(row_id=row_id)

            
            if not bidPrice or not bidVol:
                self.sell_all_row_ids(price = self.current_price)
            else:
                buy1_price = bidPrice[0]
                buy1_vol = bidVol[0]
                if len(bidPrice) > 1 and len(bidVol) > 1:
                    buy2_price = bidPrice[1]
                    buy2_vol = bidVol[1]
                else:
                    buy2_price = 0
                    buy2_vol = 0
                if buy1_price * buy1_vol * 100 < 500000:
                    if buy2_price > 0:
                        self.sell_all_row_ids(price = buy2_price)
                    else:
                        if buy1_price > 0:
                            self.sell_all_row_ids(price = buy1_price)
                        else:
                            self.sell_all_row_ids(price = self.current_price)
                else:
                    if buy1_price > 0:
                        self.sell_all_row_ids(price = buy1_price)
                    else:
                        self.sell_all_row_ids(price = self.current_price)


    def consume(self, data):
        if self.end:
            return
        logger.info(f"{self.stock_code} {self.stock_name} 监控器接收到数据 {data}")
        self.bq.put(data)

    def sell(self, price, volume):
        pass

    def add_to_sell(self, row_id):
        if row_id not in self.to_sell_row_ids:
            self.to_sell_row_ids.append(row_id)


    def sell_all_row_ids(self, price):
        all_volume = 0
        extra_infos = []
        for row_id in self.to_sell_row_ids:
            if row_id in self.left_row_ids:
                self.left_row_ids.remove(row_id)
            if row_id not in self.row_id_to_monitor_data:
                continue
            data_dict = self.row_id_to_monitor_data[row_id]
            strategy_name = data_dict['strategy_name']
            trade_price = data_dict['trade_price']
            limit_down_price = data_dict['limit_down_price']
            limit_up_price = data_dict['limit_up_price']
            left_volume = data_dict['left_volume']
            origin_row_id = data_dict['origin_row_id']
            current_trade_days = data_dict['current_trade_days']
            monitor_type = data_dict['monitor_type']
            if left_volume <= 0:
                continue
            if row_id in self.selled_row_ids:
                continue
            all_volume = all_volume + left_volume
            self.selled_row_ids.append(row_id)
            extra_infos.append((self.stock_code, left_volume, trade_price, origin_row_id, strategy_name, current_trade_days,'max_days', left_volume))
        self.to_sell_row_ids.clear()
        if all_volume > 0:
            logger.info(f"卖出 {self.stock_code} {self.stock_name} {all_volume} {price} {extra_infos}")
            if self.qmt_trader != None:
                self.qmt_trader.sell_quickly(self.stock_code, self.stock_name, all_volume, order_remark= "sell_once",  buffer=0, extra_infos = extra_infos, up_sell=True, s_price = price, limit_up_monitor = True)


    def sell_all(self, price):
        all_volume = 0
        extra_infos = []
        for row_id, data_dict in self.row_id_to_monitor_data.items():
            if row_id in self.left_row_ids:
                self.left_row_ids.remove(row_id)
            strategy_name = data_dict['strategy_name']
            trade_price = data_dict['trade_price']
            limit_down_price = data_dict['limit_down_price']
            limit_up_price = data_dict['limit_up_price']
            left_volume = data_dict['left_volume']
            origin_row_id = data_dict['origin_row_id']
            current_trade_days = data_dict['current_trade_days']
            monitor_type = data_dict['monitor_type']
            if left_volume <= 0:
                continue
            if row_id in self.selled_row_ids:
                continue
            all_volume = all_volume + left_volume
            self.selled_row_ids.append(row_id)
            extra_infos.append((self.stock_code, left_volume, trade_price, origin_row_id, strategy_name, current_trade_days,'max_days', left_volume))
        if all_volume > 0:
            logger.info(f"卖出 {self.stock_code} {self.stock_name} {all_volume} {price} {extra_infos}")
            if self.qmt_trader != None:
                self.qmt_trader.sell_quickly(self.stock_code, self.stock_name, all_volume, order_remark= "sell_all",  buffer=0, extra_infos = extra_infos, up_sell=True, s_price = price, limit_up_monitor = True)


        # (stock_code, left_volume, trade_price, row_id, strategy_name, trade_day, reason, all_volume)