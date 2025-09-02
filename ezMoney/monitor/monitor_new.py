from common import constants
from sqlite_processor.mysqlite import SQLiteManager
import threading
import queue
from date_utils import date
import datetime
from logger import strategy_logger as logger
from collections import deque
from monitor.kline_strategy import SimplifiedKLineStrategy

def calculate_seconds_difference(specified_time):
    current_time = datetime.datetime.now().timestamp()
    time_difference =  current_time - (specified_time / 1000)
    return time_difference

monitor_table = 'monitor_data'
monitor_config_table = "strategy_monitor_config"

class SmoothFilter:
    def __init__(self, window_size=10):
        self.window = deque(maxlen=window_size)  # 滑动窗口
        self.smoothed_value = 0
        
    def update(self, new_value):
        self.window.append(new_value)
        self.smoothed_value = sum(self.window)/len(self.window)
        return self.smoothed_value

class StockMonitor(object):
    def __init__(self, stock_code, stock_name, qmt_trader=None, mkt_datas=None):
        self.monitor_configs = {}
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.mkt_datas = mkt_datas
        self.qmt_trader = qmt_trader
        
        # 初始化均线数据
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
                        
        self.open_status = -1
        self.end = False
        
        # 初始化价格相关变量
        self.avg_price = 0
        self.current_price = 0
        self.smooth_current_price = 0
        self.smooth_price_filter = SmoothFilter(window_size=3)
        self.max_limit_up_vol = -1
        self.open_price = 0
        self.last_close_price = 0
        self.current_tick_steps = -1
        self.current_open_increase = 0
        self.current_increase = 0
        self.current_smooth_increase = 0
        self.zb_times = 0
        self.current_max_price = 0
        self.smooth_current_max_price = 0
        self.current_min_price = 200000
        self.current_max_open_increase = -1
        self.current_min_open_increase = -1
        self.current_max_increase = -1
        self.current_min_increase = -1
        self.limit_up_status = False
        self.limit_down_status = False
        self.limit_up_price = -1
        self.limit_down_price = -1
        self.limit_up_tick_times = -1
        
        # 初始化K线策略相关变量
        self.kline_strategies = {}  # 每个row_id对应一个策略实例
        self.stagnation_signals = {}
        self.decline_signals = {}
        
        # 初始化监控数据存储
        self.selled_row_ids = []
        self.to_sell_row_ids = []
        self.left_row_ids = []
        self.bq = queue.Queue()
        self.row_id_to_monitor_data = {}
        self.monitor_type_to_row_ids = {}
        self.running_monitor_status = {}
        self.running_monitor_stock_status = {}
        self.running_monitor_down_status = {}
        self.running_monitor_observe_steps = {}
        self.pre_avg_volumes = {}  # 每个row_id对应的历史成交量数据

        # 从数据库加载监控数据
        with SQLiteManager(constants.db_path) as db:
            self.query_data_lists = db.query_data_dict(monitor_table, condition_dict= {'date_key': date.get_current_date(), 'stock_code': stock_code, 'monitor_status': 1})
            if not self.query_data_lists:
                logger.error(f"query_data_lists null. {stock_code}-{stock_name}")
                
            for query_data in self.query_data_lists:
                row_id = query_data['id']
                origin_row_id = query_data['origin_row_id']

                trade_datas = db.query_data_dict("trade_data", {"id": origin_row_id})
                if not trade_datas:
                    continue
                    
                trade_data = trade_datas[0]
                order_type = trade_data['order_type']
                order_price = trade_data['order_price']
                origin_trade_price = trade_data['trade_price']
                
                if order_type == 1:
                    query_data['origin_trade_price'] = order_price
                else:
                    query_data['origin_trade_price'] = origin_trade_price
                    
                strategy_name = query_data['strategy_name']
                sub_strategy_name = query_data['sub_strategy_name']
                               
                if row_id not in self.left_row_ids:
                    self.left_row_ids.append(row_id)
                                        
                if row_id not in self.running_monitor_status:
                    self.running_monitor_status[row_id] = constants.StockStatus.COLD_START
                    
                if row_id not in self.running_monitor_stock_status:
                    self.running_monitor_stock_status[row_id] = constants.StockStatus.UNKNOWN
                    
                if row_id not in self.running_monitor_observe_steps:
                    self.running_monitor_observe_steps[row_id] = 0
                    
                if row_id not in self.running_monitor_down_status:
                    self.running_monitor_down_status[row_id] = False
                    
                self.row_id_to_monitor_data[row_id] = query_data
                monitor_type = query_data['monitor_type']
                
                # 获取监控配置
                monitor_config = db.query_data_dict(monitor_config_table, condition_dict= {'strategy_name': strategy_name})
                default_monitor_config = db.query_data_dict(monitor_config_table, condition_dict= {'strategy_name': 'default'})
                
                if not monitor_config and not default_monitor_config:
                    logger.error(f"monitor_config null. {strategy_name}")
                    continue
                    
                if not monitor_config:
                    monitor_config = default_monitor_config
                    
                monitor_config = monitor_config[0]
                self.monitor_configs[strategy_name] = monitor_config
                
                # 初始化K线策略
                stagnation_kline_ticks = monitor_config.get('stagnation_kline_ticks', 10)
                decline_kline_ticks = monitor_config.get('decline_kline_ticks', 15)
                yang_yin_threshold = monitor_config.get('yang_yin_threshold', 0.002)
                stagnation_n = monitor_config.get('stagnation_n', 10)
                stagnation_volume_ratio_threshold = monitor_config.get('stagnation_volume_ratio_threshold', 2.5)
                stagnation_ratio_threshold = monitor_config.get('stagnation_ratio_threshold', 40)
                decline_volume_ratio_threshold = monitor_config.get('decline_volume_ratio_threshold', 2.5)
                max_rebounds = monitor_config.get('max_rebounds', 2)
                decline_ratio_threshold = monitor_config.get('decline_ratio_threshold', 50)
                
                self.kline_strategies[row_id] = SimplifiedKLineStrategy(
                    stagnation_kline_ticks=stagnation_kline_ticks,
                    decline_kline_ticks=decline_kline_ticks,
                    yang_yin_threshold=yang_yin_threshold,
                    stagnation_n=stagnation_n,
                    stagnation_volume_ratio_threshold=stagnation_volume_ratio_threshold,
                    stagnation_ratio_threshold=stagnation_ratio_threshold,
                    decline_volume_ratio_threshold=decline_volume_ratio_threshold,
                    max_rebounds=max_rebounds,
                    decline_ratio_threshold=decline_ratio_threshold
                )
                
                # 获取历史成交量数据
                self.pre_avg_volumes[row_id] = self.get_pre_avg_volumes(stock_code, db)
                
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
        
    def get_pre_avg_volumes(self, stock_code, db):
        # 这里需要实现获取历史成交量数据的逻辑
        # 返回一个列表，包含前几日的平均成交量
        # 简化实现，返回空列表
        return []
        
    def start_monitor(self):
        logger.info(f"start monitor {self.stock_code} {self.stock_name}")
        self.thread = threading.Thread(target=self.monitor)
        self.thread.setDaemon(True)
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
            
            # 更新价格数据
            self.avg_price = amount / volume / 100
            self.current_price = lastPrice
            self.smooth_current_price = self.smooth_price_filter.update(self.current_price)
            self.open_price = open
            self.last_close_price = lastClose
            self.current_tick_steps = self.current_tick_steps + 1
            self.current_open_increase = (self.current_price - self.open_price) / self.open_price
            self.current_increase = (self.current_price - self.last_close_price) / self.last_close_price
            self.current_smooth_increase = (self.smooth_current_price - self.last_close_price) / self.last_close_price
            self.current_max_price = max(self.current_max_price, high)
            self.smooth_current_max_price = max(self.smooth_current_max_price, self.smooth_current_price)
            self.current_min_price = min(self.current_min_price, low)
            self.current_max_open_increase = (self.current_max_price - self.open_price) / self.open_price
            self.current_min_open_increase = (self.current_min_price - self.open_price) / self.open_price
            self.current_max_increase = (self.current_max_price - self.last_close_price) / self.last_close_price
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

            # 更新K线策略
            cur_volume = volume - pvolume
            for row_id, kline_strategy in self.kline_strategies.items():
                if row_id in self.selled_row_ids:
                    continue
                    
                if not kline_strategy.initialized and open:
                    kline_strategy.initialize(open, open)
                    
                cur_prevolume = self.pre_avg_volumes[row_id][self.current_tick_steps] if self.current_tick_steps < len(self.pre_avg_volumes[row_id]) else 0
                
                monitor_data = self.row_id_to_monitor_data[row_id]
                strategy_name = monitor_data['strategy_name']
                monitor_config = self.monitor_configs.get(strategy_name, {})
                flzz_use_smooth_price = monitor_config.get('flzz_use_smooth_price', False)
                
                if flzz_use_smooth_price:
                    kline_strategy.update_tick_data(cur_volume, self.smooth_current_price, cur_prevolume, self.avg_price)
                else:
                    kline_strategy.update_tick_data(cur_volume, lastPrice, cur_prevolume, self.avg_price)
                    
                self.stagnation_signals[row_id], self.decline_signals[row_id] = kline_strategy.generate_signals()
                
                # 检查K线策略信号
                use_simiple_kline_strategy = monitor_config.get('use_simiple_kline_strategy', True)
                use_simiple_kline_strategy_flxd = monitor_config.get('use_simiple_kline_strategy_flxd', True)
                use_simiple_kline_strategy_flzz = monitor_config.get('use_simiple_kline_strategy_flzz', True)
                flxd_ticks = monitor_config.get('flxd_ticks', 110)
                flzz_ticks = monitor_config.get('flzz_ticks', 5000)
                kline_sell_only_zy = monitor_config.get('kline_sell_only_zy', False)
                flzz_zf_thresh = monitor_config.get('flzz_zf_thresh', 0.03)
                monitor_type = monitor_data.get('monitor_type', -1)
                
                if (use_simiple_kline_strategy_flxd and use_simiple_kline_strategy and 
                    self.current_tick_steps <= flxd_ticks and self.decline_signals[row_id]):
                    if not kline_sell_only_zy or (kline_sell_only_zy and monitor_type == 1):
                        self.add_to_sell(row_id=row_id)
                        continue
                        
                if (use_simiple_kline_strategy_flzz and use_simiple_kline_strategy and 
                    self.current_tick_steps <= flzz_ticks and self.stagnation_signals[row_id] and 
                    self.current_increase >= flzz_zf_thresh):
                    if not kline_sell_only_zy or (kline_sell_only_zy and monitor_type == 1):
                        self.add_to_sell(row_id=row_id)
                        continue

            if self.limit_up_price < 0 or self.limit_down_price < 0:
                limit_down_price_0, limit_up_price_0 = constants.get_limit_price(self.last_close_price, stock_code=self.stock_code)
                self.limit_up_price = limit_up_price_0
                self.limit_down_price = limit_down_price_0

            if self.limit_up_price > 0 and abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
                if not bidPrice or not bidVol:
                    self.sell_all(price=self.current_price)
                    continue
                    
                self.max_limit_up_vol = max(self.max_limit_up_vol, bidVol[0])

                buy1_price = bidPrice[0]
                buy1_vol = bidVol[0]
                if abs(buy1_price - self.limit_up_price) >= 0.01:
                    if buy1_price > 0:
                        self.sell_all(price=buy1_price)
                    else:
                        self.sell_all(price=self.current_price)
                    continue
                
                if self.limit_up_status:
                    self.limit_up_tick_times = self.limit_up_tick_times + 1
                    
                    # 使用配置参数
                    default_config = next(iter(self.monitor_configs.values())) if self.monitor_configs else {}
                    fd_juge_ticks = default_config.get('fd_juge_ticks', 5)
                    fd_mount = default_config.get('fd_mount', 35000000)
                    fd_vol_pct = default_config.get('fd_vol_pct', 0.5)
                    
                    if self.limit_up_tick_times > fd_juge_ticks:
                        if not bidPrice or not bidVol:
                            self.sell_all(price=self.current_price)
                            continue
                            
                        buy1_price = bidPrice[0]
                        buy1_vol = bidVol[0]
                        if abs(buy1_price - self.limit_up_price) >= 0.01:
                            if buy1_price > 0:
                                self.sell_all(price=buy1_price)
                            else:
                                self.sell_all(price=self.current_price)
                            continue
                            
                        # 封单金额过小 卖
                        if buy1_price * buy1_vol * 100 < fd_mount and buy1_vol / self.max_limit_up_vol < fd_vol_pct:
                            logger.info(f"封单金额过小，卖出 {self.stock_code} {self.stock_name}")
                            if buy1_price > 0:
                                self.sell_all(price=buy1_price)
                            else:
                                self.sell_all(price=self.current_price)
                            continue
                else:
                    self.limit_up_tick_times = 0
                    self.limit_up_status = True

            elif self.limit_up_price > 0 and abs(self.smooth_current_price - self.limit_up_price) >= 0.0033:
                self.max_limit_up_vol = -1
                
                if self.limit_up_status:
                    # 涨停炸板卖
                    self.zb_times = self.zb_times + 1
                    
                    # 使用配置参数
                    default_config = next(iter(self.monitor_configs.values())) if self.monitor_configs else {}
                    max_zb_times = default_config.get('max_zb_times', 1)
                    
                    if self.zb_times > max_zb_times:
                        logger.info(f"炸板了，卖出 {self.stock_code} {self.stock_name}")
                        if not bidPrice or not bidVol:
                            self.sell_all(price=self.current_price)
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
                                    self.sell_all(price=buy2_price)
                                else:
                                    if buy1_price > 0:
                                        self.sell_all(price=buy1_price)
                                    else:
                                        self.sell_all(price=self.current_price)
                            else:
                                if buy1_price > 0:
                                    self.sell_all(price=buy1_price)
                                else:
                                    self.sell_all(price=self.current_price)
                        self.limit_up_status = False
                        self.limit_up_tick_times = -1
                        continue
                self.limit_up_tick_times = -1
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
            
            # 处理不同类型的监控任务
            for monitor_type, row_ids in self.monitor_type_to_row_ids.items():
                if not row_ids:
                    continue
                    
                for row_id in row_ids:
                    if row_id in self.selled_row_ids:
                        continue
                        
                    monitor_data = self.row_id_to_monitor_data[row_id]
                    strategy_name = monitor_data['strategy_name']
                    
                    if strategy_name not in self.monitor_configs:
                        logger.error(f"策略{strategy_name} 无配置 跳过")
                        if row_id not in self.selled_row_ids:
                            self.selled_row_ids.append(row_id)
                        if row_id in self.left_row_ids:
                            self.left_row_ids.remove(row_id)
                        continue
                        
                    monitor_config = self.monitor_configs[strategy_name]
                    
                    if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                        # 止盈逻辑处理
                        trade_price = monitor_data['trade_price']
                        origin_trade_price = monitor_data['origin_trade_price']
                        limit_down_price = monitor_data.get('limit_down_price', self.limit_down_price)
                        limit_up_price = monitor_data.get('limit_up_price', self.limit_up_price)
                        
                        per_step_tick_gap = monitor_config.get('per_step_tick_gap', 3)
                        cold_start_steps = monitor_config.get('cold_start_steps', 10)
                        max_abserve_tick_steps = monitor_config.get('max_abserve_tick_steps', 110)
                        max_abserce_avg_price_down_steps = monitor_config.get('max_abserce_avg_price_down_steps', 1)
                        stop_profit_open_hc_pct = monitor_config.get('stop_profit_open_hc_pct', -0.05)
                        stop_profit_pct = monitor_config.get('stop_profit_pct', 0)
                        dynamic_hc_stop_profit_thres = monitor_config.get('dynamic_hc_stop_profit_thres', 1.5)
                        static_hc_stop_profit_pct = monitor_config.get('static_hc_stop_profit_pct', 1)
                        last_close_price_hc_pct = monitor_config.get('last_close_price_hc_pct', -0.005)

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

                        open_hc_line = self.open_price * (1 + stop_profit_open_hc_pct)
                        stop_profit_line = origin_trade_price * (1 + stop_profit_pct)
                        zs_line = max(open_hc_line, stop_profit_line)

                        logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 动态止盈线: {dynamic_zs_line:.2f}, 静态止盈线: {static_zs_line:.2f}, 止损线: {zs_line:.2f}")

                        if self.current_tick_steps < cold_start_steps:
                            continue
                        elif self.current_tick_steps == cold_start_steps:
                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                            elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP

                            if self.current_price <= self.avg_price:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                            else:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP

                            self.running_monitor_down_status[row_id] = False
                            self.running_monitor_observe_steps[row_id] = 0

                        elif self.current_tick_steps > cold_start_steps:
                            if self.current_tick_steps % per_step_tick_gap == 0:
                                # 这里省略具体的止盈逻辑处理，与回测代码类似
                                # 需要根据running_monitor_status和running_monitor_stock_status进行状态判断
                                # 并在适当条件下调用self.add_to_sell(row_id=row_id)
                                pass
                                
                    elif monitor_type == constants.STOP_LOSS_TRADE_TYPE:
                        # 止损逻辑处理
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data.get('limit_down_price', self.limit_down_price)
                        limit_up_price = monitor_data.get('limit_up_price', self.limit_up_price)
                        
                        per_step_tick_gap = monitor_config.get('per_step_tick_gap', 3)
                        cold_start_steps = monitor_config.get('cold_start_steps', 10)
                        max_abserve_tick_steps = monitor_config.get('max_abserve_tick_steps', 110)
                        max_abserce_avg_price_down_steps = monitor_config.get('max_abserce_avg_price_down_steps', 1)
                        dynamic_hc_stop_profit_thres = monitor_config.get('dynamic_hc_stop_profit_thres', 1.5)
                        static_hc_stop_profit_pct = monitor_config.get('static_hc_stop_profit_pct', 1)
                        last_close_price_hc_pct = monitor_config.get('last_close_price_hc_pct', -0.005)
                        
                        # 这里省略具体的止损逻辑处理，与回测代码类似
                        
                    elif monitor_type == constants.LAST_TRADE_DAY_TRADE_TYPE:
                        # 最后交易日逻辑处理
                        trade_price = monitor_data['trade_price']
                        last_day_sell_thres = monitor_config.get('last_day_sell_thres', 0.086)
                        last_day_sell_huiche = monitor_config.get('last_day_sell_huiche', 0.009)
                        
                        max_thres_line = self.smooth_current_max_price * (1 - last_day_sell_huiche)
                        if self.current_increase > last_day_sell_thres and self.current_price < max_thres_line:
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 回撤卖出")
                            self.add_to_sell(row_id=row_id)
                            continue
            
            # 检查是否需要全部卖出
            if not bidPrice or not bidVol:
                self.sell_all_row_ids(price=self.current_price)
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
                        self.sell_all_row_ids(price=buy2_price)
                    else:
                        if buy1_price > 0:
                            self.sell_all_row_ids(price=buy1_price)
                        else:
                            self.sell_all_row_ids(price=self.current_price)
                else:
                    if buy1_price > 0:
                        self.sell_all_row_ids(price=buy1_price)
                    else:
                        self.sell_all_row_ids(price=self.current_price)

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
        if not self.qmt_trader:
            return
            
        position_stocks = self.qmt_trader.get_tradable_stocks()
        if not position_stocks:
            return
        
        available_qty = 0
        for position_stock_info in position_stocks:
            stock_code = position_stock_info['stock_code']
            if stock_code == self.stock_code:
                available_qty = position_stock_info['available_qty']
                break
                
        if available_qty <= 0:
            logger.info(f"股票 {self.stock_code} {self.stock_name} 无可用量 无法卖出")
            return
            
        all_volume = 0
        extra_infos = []
        temp_to_sell_row_ids = self.to_sell_row_ids[:]
        self.to_sell_row_ids.clear()
        
        for row_id in temp_to_sell_row_ids:
            if all_volume >= available_qty:
                self.to_sell_row_ids.append(row_id)
                continue
                
            if row_id not in self.row_id_to_monitor_data:
                continue
                
            data_dict = self.row_id_to_monitor_data[row_id]
            left_volume = data_dict['left_volume']
            
            if left_volume <= 0:
                continue
                
            can_sell = min(left_volume, available_qty - all_volume)
            data_dict['left_volume'] = left_volume - can_sell
            all_volume += can_sell
            
            strategy_name = data_dict['strategy_name']
            trade_price = data_dict['trade_price']
            origin_row_id = data_dict['origin_row_id']
            current_trade_days = data_dict['current_trade_days']
            
            extra_infos.append((
                self.stock_code, 
                can_sell,
                trade_price, 
                origin_row_id, 
                strategy_name, 
                current_trade_days,
                'max_days', 
                can_sell
            ))
            
            if data_dict['left_volume'] == 0:
                self.selled_row_ids.append(row_id)
                if row_id in self.left_row_ids:
                    self.left_row_ids.remove(row_id)
                logger.debug(f"完全卖出 row_id={row_id}, 数量={can_sell}")
            else:
                logger.info(f"部分卖出 row_id={row_id}, 卖出={can_sell}, 剩余={data_dict['left_volume']}")
        
        if all_volume > 0:
            logger.info(f"执行卖出 {self.stock_code} {self.stock_name} 总量={all_volume} 价格={price}")
            self.qmt_trader.sell_quickly(
                self.stock_code, 
                self.stock_name, 
                all_volume, 
                order_remark="sell_once",  
                buffer=0, 
                extra_infos=extra_infos, 
                up_sell=True, 
                s_price=price, 
                limit_up_monitor=True
            )
        else:
            logger.info(f"无有效卖出量 {self.stock_code} {self.stock_name}")

    def sell_all(self, price):
        if not self.qmt_trader:
            return
            
        position_stocks = self.qmt_trader.get_tradable_stocks()
        if not position_stocks:
            return
        
        available_qty = 0
        for position_stock_info in position_stocks:
            if position_stock_info['stock_code'] == self.stock_code:
                available_qty = position_stock_info['available_qty']
                break
                
        if available_qty <= 0:
            logger.info(f"股票 {self.stock_code} {self.stock_name} 无可用量 无法卖出")
            return
            
        all_volume = 0
        extra_infos = []
        temp_row_ids = list(self.row_id_to_monitor_data.keys())
        
        for row_id in temp_row_ids:
            if all_volume >= available_qty:
                break
                
            data_dict = self.row_id_to_monitor_data.get(row_id)
            if not data_dict:
                continue
                
            left_volume = data_dict.get('left_volume', 0)
            if left_volume <= 0 or row_id in self.selled_row_ids:
                continue
                
            can_sell = min(left_volume, available_qty - all_volume)
            data_dict['left_volume'] = left_volume - can_sell
            all_volume += can_sell
            
            strategy_name = data_dict.get('strategy_name', '')
            trade_price = data_dict.get('trade_price', 0.0)
            origin_row_id = data_dict.get('origin_row_id', '')
            current_trade_days = data_dict.get('current_trade_days', 0)
            
            extra_infos.append((
                self.stock_code, 
                can_sell,
                trade_price, 
                origin_row_id, 
                strategy_name, 
                current_trade_days,
                'max_days', 
                can_sell
            ))
            
            if data_dict['left_volume'] == 0:
                self.selled_row_ids.append(row_id)
                if row_id in self.left_row_ids:
                    self.left_row_ids.remove(row_id)
                logger.debug(f"完全卖出 row_id={row_id}, 数量={can_sell}")
            else:
                logger.info(f"部分卖出 row_id={row_id}, 卖出={can_sell}, 剩余={data_dict['left_volume']}")
        
        if all_volume > 0:
            logger.info(f"执行全部卖出 {self.stock_code} {self.stock_name} 总量={all_volume} 价格={price}")
            self.qmt_trader.sell_quickly(
                self.stock_code, 
                self.stock_name, 
                all_volume, 
                order_remark="sell_all",  
                buffer=0, 
                extra_infos=extra_infos, 
                up_sell=True, 
                s_price=price, 
                limit_up_monitor=True
            )
        else:
            logger.info(f"无有效卖出量 {self.stock_code} {self.stock_name}")