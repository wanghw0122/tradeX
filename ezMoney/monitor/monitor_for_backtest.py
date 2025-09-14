import sys
sys.path.append(r"D:\workspace\TradeX\ezMoney")
from common import constants
import os
import logging
import datetime
from logger import strategy_logger as logger

from collections import deque
from monitor.kline_strategy import SimplifiedKLineStrategy


class SmoothFilter:
    def __init__(self, window_size=3):
        self.window = deque(maxlen=window_size)  # 滑动窗口
        self.smoothed_value = 0
        
    def update(self, new_value):
        self.window.append(new_value)
        self.smoothed_value = sum(self.window)/len(self.window)
        return self.smoothed_value

class StockMonitor(object):
    def __init__(self, stock_code, stock_name, stock_infos = {}, mkt_datas = None, params = {}):
        # self.config = {}
        self.monitor_configs = {}
        self.logger = self._create_process_safe_logger()
        # self.config['step_tick_gap'] = 5
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.mkt_datas = mkt_datas
        self.stock_infos = stock_infos

        self.strategy_name = stock_infos.get('strategy_name', 'test')

        self.order_price = stock_infos.get('order_price', 0)
        self.trade_price = stock_infos.get('trade_price', 0)
        self.origin_trade_price = stock_infos.get('origin_trade_price', 0)
        self.limit_up_price = stock_infos.get('limit_up_price', -1)
        self.limit_down_price = stock_infos.get('limit_down_price', -1)
        self.row_id = stock_infos.get('row_id', 0)
        self.monitor_type = stock_infos.get('monitor_type', -1)
        self.tick_datas = stock_infos.get('tick_datas', [])
        self.pre_avg_volumes = stock_infos.get('pre_avg_volumes', [])
        self.pre_volume = stock_infos.get('n_pre_volume', -1)

        self.stagnation_kline_ticks = params.get('stagnation_kline_ticks', 10)
        self.decline_kline_ticks = params.get('decline_kline_ticks', 15)
        self.yang_yin_threshold = params.get('yang_yin_threshold', 0.002)
        self.stagnation_n = params.get('stagnation_n', 10)
        self.stagnation_volume_ratio_threshold = params.get('stagnation_volume_ratio_threshold', 2.5)
        self.stagnation_ratio_threshold = params.get('stagnation_ratio_threshold', 40)
        self.decline_volume_ratio_threshold = params.get('decline_volume_ratio_threshold', 2.5)
        self.max_rebounds = params.get('max_rebounds', 2)
        self.decline_ratio_threshold = params.get('decline_ratio_threshold', 50)
        self.window_size = params.get('window_size', 3)

        self.use_simiple_kline_strategy = params.get('use_simiple_kline_strategy', True)

        self.use_simiple_kline_strategy_flxd = params.get('use_simiple_kline_strategy_flxd', True)
        self.use_simiple_kline_strategy_flzz = params.get('use_simiple_kline_strategy_flzz', True)

        self.flxd_ticks = params.get('flxd_ticks', 110)

        self.flzz_ticks = params.get('flzz_ticks', 5000)

        self.kline_sell_only_zy = params.get('kline_sell_only_zy', False)

        self.kline_sell_flxd_zy = params.get('kline_sell_flxd_zy', False)
        self.kline_sell_flxd_zs = params.get('kline_sell_flxd_zs', False)
        self.kline_sell_flzz_zs = params.get('kline_sell_flzz_zs', False)
        self.kline_sell_flzz_zy = params.get('kline_sell_flzz_zy', False)
        self.flzz_use_smooth_price = params.get('flzz_use_smooth_price', False)

        self.flzz_zf_thresh = params.get('flzz_zf_thresh', 0.03)

        if self.use_simiple_kline_strategy:
            self.kline_strategy = SimplifiedKLineStrategy(stagnation_kline_ticks = self.stagnation_kline_ticks, 
                                                          decline_kline_ticks = self.decline_kline_ticks, 
                                                          yang_yin_threshold = self.yang_yin_threshold, 
                                                          stagnation_n = self.stagnation_n, 
                                                          stagnation_volume_ratio_threshold = self.stagnation_volume_ratio_threshold, 
                                                          stagnation_ratio_threshold = self.stagnation_ratio_threshold, 
                                                          decline_volume_ratio_threshold = self.decline_volume_ratio_threshold, 
                                                          max_rebounds = self.max_rebounds, 
                                                          decline_ratio_threshold = self.decline_ratio_threshold)

        else:
            self.kline_strategy = None

        self.stagnation_signal, self.decline_signal = 0, 0

        # print(f' {self.stock_code} tick_datas {len(self.tick_datas)}')

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
        
        self.params = params

        self.per_step_tick_gap = params.get('per_step_tick_gap', 3)
        self.cold_start_steps = params.get('cold_start_steps', 10)
        self.max_abserve_tick_steps = params.get('max_abserve_tick_steps', 110)
        self.max_abserce_avg_price_down_steps = params.get('max_abserce_avg_price_down_steps', 1)
        self.stop_profit_open_hc_pct = params.get('stop_profit_open_hc_pct', -0.05)
        self.stop_profit_pct = params.get('stop_profit_pct', 0)
        self.dynamic_hc_stop_profit_thres = params.get('dynamic_hc_stop_profit_thres', 1.5)
        self.static_hc_stop_profit_pct = params.get('static_hc_stop_profit_pct', 1)
        self.last_close_price_hc_pct = params.get('last_close_price_hc_pct', -0.005)
        self.last_open_price_hc_pct = params.get('last_open_price_hc_pct', -0.005)

        self.last_day_sell_thres = params.get('last_day_sell_thres',0.086)

        self.last_day_sell_huiche = params.get('last_day_sell_huiche', 0.009)
        self.open_price_max_hc = params.get('open_price_max_hc', -0.05)

        self.loss_per_step_tick_gap = params.get('loss_per_step_tick_gap', 3)
        self.loss_cold_start_steps = params.get('loss_cold_start_steps', 10)
        self.loss_max_abserve_tick_steps = params.get('loss_max_abserve_tick_steps', 110)
        self.loss_max_abserce_avg_price_down_steps = params.get('loss_max_abserce_avg_price_down_steps', 1)

        self.loss_dynamic_hc_stop_profit_thres = params.get('loss_dynamic_hc_stop_profit_thres', 1.5)
        self.loss_static_hc_stop_profit_pct = params.get('loss_static_hc_stop_profit_pct', 1)
        self.loss_last_close_price_hc_pct = params.get('loss_last_close_price_hc_pct', -0.005)
        self.loss_last_open_price_hc_pct = params.get('loss_last_open_price_hc_pct', -0.005)
        self.loss_open_price_max_hc = params.get('loss_open_price_max_hc', -0.05)
        self.down_open_sell_wait_time = params.get('down_open_sell_wait_time', False)
        self.loss_down_open_sell_wait_time = params.get('loss_down_open_sell_wait_time', False)
        
        self.fd_mount = params.get('fd_mount', 30000000)
        self.fd_vol_pct = params.get('fd_vol_pct', 0.24)
        self.fd_juge_ticks = params.get('fd_ju_ticks', 3)

        self.max_zb_times = params.get('max_zb_times', 2)

        self.open_status = -1

        self.monitor_data = {}
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
        # 平滑当天涨幅
        self.current_smooth_increase = 0

        # 当天最高价
        self.current_max_price = 0
        # 当天平滑最高价
        self.smooth_current_max_price = 0
        # 当天最低价
        self.current_min_price = 200000
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

        self.limit_up_tick_times = -1

        self.running_monitor_status = {}
        self.running_monitor_stock_status = {}

        self.running_monitor_down_status = {}

        self.running_monitor_observe_steps = {}

        self.zb_times = 0
       
        if self.row_id not in self.running_monitor_status:
            self.running_monitor_status[self.row_id] = constants.StockStatus.COLD_START
        if self.row_id not in self.running_monitor_stock_status:
            self.running_monitor_stock_status[self.row_id] = constants.StockStatus.UNKNOWN
        if self.row_id not in self.running_monitor_observe_steps:
            self.running_monitor_observe_steps[self.row_id] = 0
        if self.row_id not in self.running_monitor_down_status:
            self.running_monitor_down_status[self.row_id] = False
        
        self.sell_success = False
        self.sell_price = 0

        for data in self.tick_datas:
            monitor_result = self.monitor(data)
            if not monitor_result:
                continue
            else:
                selled, sell_price = monitor_result
                if not selled:
                    continue
                if selled:
                    self.sell_success = True
                    self.sell_price = sell_price
                    break

    def get_result(self):
        """返回监控结果元组 (是否卖出, 卖出价格)"""
        return (self.sell_success, self.sell_price, self.current_tick_steps)

    # def _create_process_safe_logger(self):
    #     """创建进程安全的日志记录器"""
    #     # 获取当前进程ID
    #     pid = os.getpid()
        
    #     # 创建日志目录
    #     log_dir = "logs/strategy_logger"
    #     os.makedirs(log_dir, exist_ok=True)
        
    #     # 创建进程特定的日志文件
    #     log_file = os.path.join(log_dir, f"strategy_logger_{pid}.log")
        
    #     # 创建日志记录器
    #     logger = logging.getLogger(f"StockMonitor_{pid}")
    #     logger.setLevel(logging.INFO)
        
    #     # 添加文件处理器
    #     file_handler = logging.FileHandler(log_file)
    #     file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
    #     # 禁用文件轮转
    #     file_handler.doRollover = lambda: None
        
    #     logger.addHandler(file_handler)
        
    #     return logger
    
    def _create_process_safe_logger(self):
        """创建进程安全的日志记录器（静默模式）"""
        # 获取当前进程ID
        pid = os.getpid()
        
        # 创建日志记录器
        logger = logging.getLogger(f"StockMonitor_{pid}")
        logger.setLevel(logging.CRITICAL + 1)  # 设置为不记录任何级别的日志
        logger.propagate = False  # 阻止日志传播
        
        return logger

    def monitor(self, data):

        lastPrice = data['lastPrice']
        open = data['open']
        high = data['high']
        low = data['low']
        lastClose = data['lastClose']
        volume = data['volume']
        amount = data['amount']
        # pvolume = data['pvolume'] if data['pvolume'] > 0 else 1
        askPrice = data['askPrice']
        bidPrice = data['bidPrice']
        askVol = data['askVol']
        bidVol = data['bidVol']
        if open and self.kline_strategy and not self.kline_strategy.initialized:
            self.kline_strategy.initialize(open, open)

        if self.open_status == -1:
            self.open_status = constants.OpenStatus.DOWN_OPEN if open <= lastClose else constants.OpenStatus.UP_OPEN
        if amount <= 0 or volume <= 0:
            raise ValueError("amount or volume is 0")
        if lastPrice <= 0:
            return False, lastPrice
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

        cur_volume = volume - self.pre_volume
        self.pre_volume = volume
        # 当前天内涨幅
        self.current_open_increase = (self.current_price - self.open_price) / self.open_price
        # 当天涨幅
        self.current_increase = (self.current_price - self.last_close_price) / self.last_close_price
        # 当日平滑涨幅
        self.current_smooth_increase = (self.smooth_current_price - self.last_close_price) / self.last_close_price
        # 当天最高价
        self.current_max_price = max(self.current_max_price, high)
        # 平滑最高价
        self.smooth_current_max_price = max(self.smooth_current_max_price, self.smooth_current_price)
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

        # self.logger.info(
        #     f"股票代码： {self.stock_code}, 股票名称： {self.stock_name}, "
        #     f"均价: {self.avg_price:.2f}, 当前价: {self.current_price:.2f}, 开盘价: {self.open_price:.2f}, "
        #     f"昨天收盘价: {self.last_close_price:.2f}, 当前步数: {self.current_tick_steps}, 当前volume {cur_volume} "
        #     f"当前天内涨幅: {self.current_open_increase:.2%}, 当天涨幅: {self.current_increase:.2%}, "
        #     f"当天最高价: {self.current_max_price:.2f}, 当天最低价: {self.current_min_price:.2f}, "
        #     f"当天天内最高涨幅: {self.current_max_open_increase:.2%}, 当天天内最低涨幅: {self.current_min_open_increase:.2%}, "
        #     f"当天最高涨幅: {self.current_max_increase:.2%}, 当天最低涨幅: {self.current_min_increase:.2%}"
        # )

        if self.use_simiple_kline_strategy and self.kline_strategy:
            cur_prevolume = self.pre_avg_volumes[self.current_tick_steps] if self.current_tick_steps < len(self.pre_avg_volumes) else 0
            if self.flzz_use_smooth_price:
                self.kline_strategy.update_tick_data(cur_volume, self.smooth_current_price, cur_prevolume, self.avg_price)
            else:
                self.kline_strategy.update_tick_data(cur_volume, lastPrice, cur_prevolume, self.avg_price)
            self.stagnation_signal, self.decline_signal = self.kline_strategy.generate_signals()

        if self.use_simiple_kline_strategy_flxd and self.use_simiple_kline_strategy and self.current_tick_steps <= self.flxd_ticks and self.decline_signal:
            if self.kline_sell_flxd_zy and self.monitor_type == 1:
                return True, self.current_price
            if self.kline_sell_flxd_zs and self.monitor_type == 2:
                return True, self.current_price
        if self.use_simiple_kline_strategy_flzz and self.use_simiple_kline_strategy and self.current_tick_steps <= self.flzz_ticks and self.stagnation_signal and self.current_increase >= self.flzz_zf_thresh:
            if self.kline_sell_flzz_zy and self.monitor_type == 1:
                return True, self.current_price
            if self.kline_sell_flzz_zs and self.monitor_type == 2:
                return True, self.current_price
        
        if self.limit_up_price < 0 or self.limit_down_price < 0:
            limit_down_price_0, limit_up_price_0 = constants.get_limit_price(self.last_close_price, stock_code=self.stock_code)
            self.limit_up_price = limit_up_price_0
            self.limit_down_price = limit_down_price_0

        if self.limit_up_price > 0 and abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
            if not bidPrice or not bidVol:
                return True, self.current_price

            self.max_limit_up_vol = max(self.max_limit_up_vol, bidVol[0])

            buy1_price = bidPrice[0]
            buy1_vol = bidVol[0]
            # if abs(buy1_price - self.limit_up_price) >= 0.01:
            #     if buy1_price > 0:
            #         return True, buy1_price
            #     else:
            #         return True, self.current_price
            
            if self.limit_up_status:
                self.limit_up_tick_times = self.limit_up_tick_times + 1
                if self.limit_up_tick_times > self.fd_juge_ticks:
                    if not bidPrice or not bidVol:
                        return True, self.current_price
                    buy1_price = bidPrice[0]
                    buy1_vol = bidVol[0]
                    if abs(buy1_price - self.limit_up_price) >= 0.01:
                        if buy1_price > 0:
                            return True, buy1_price
                        else:
                            return True, self.current_price
                    # 封单金额过小 卖
                    if buy1_price * buy1_vol * 100 < self.fd_mount and buy1_vol / self.max_limit_up_vol < self.fd_vol_pct:
                        self.logger.info(f"封单金额过小，卖出 {self.stock_code} {self.stock_name}")
                        if buy1_price > 0:
                            return True, buy1_price
                        else:
                            return True, self.current_price
            else:
                self.limit_up_tick_times = 0
                self.limit_up_status = True

        elif self.limit_up_price > 0 and abs(self.smooth_current_price - self.limit_up_price) >= 0.0033:
            self.max_limit_up_vol = -1
            
            if self.limit_up_status:
                self.zb_times = self.zb_times + 1
                self.limit_up_status = False
                self.limit_up_tick_times = -1
                if self.zb_times > self.max_zb_times:
                    self.logger.info(f"炸板了，卖出 {self.stock_code} {self.stock_name}")
                    if not bidPrice or not bidVol:
                        raise Exception(f"not bidPrice {self.limit_up_price} is not valid for {self.stock_code}")
                        return True, self.current_price
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
                                return True, buy2_price
                            else:
                                if buy1_price > 0:
                                    return True, buy1_price
                                else:
                                    return True, self.current_price
                        else:
                            if buy1_price > 0:
                                return True, buy1_price
                            else:
                                return True, self.current_price
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
            return False, self.current_price

        current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
    
        if self.monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
            strategy_name = self.strategy_name
            trade_price = self.trade_price
            origin_trade_price = self.origin_trade_price
            limit_down_price = self.limit_down_price
            limit_up_price = self.limit_up_price
            
            # tick的gap间隔
            per_step_tick_gap = self.per_step_tick_gap
            # 等待冷启动次数
            cold_start_steps = self.cold_start_steps
            # 最大观察的tick数量
            max_abserve_tick_steps = self.max_abserve_tick_steps
            # 跌落均线下观察的tick数量
            max_abserce_avg_price_down_steps = self.max_abserce_avg_price_down_steps
            # 止盈的开盘最大下跌
            stop_profit_open_hc_pct = self.stop_profit_open_hc_pct
            # 止盈的最小止盈点
            stop_profit_pct = self.stop_profit_pct
            # 动态回撤的系数
            dynamic_hc_stop_profit_thres = self.dynamic_hc_stop_profit_thres
            # 静态回撤的幅度
            static_hc_stop_profit_pct = self.static_hc_stop_profit_pct
            # 前一天收盘价的水下容忍比例
            last_close_price_hc_pct = self.last_close_price_hc_pct
            last_open_price_hc_pct = self.last_open_price_hc_pct

            open_price_max_hc = self.open_price_max_hc

            down_open_sell_wait_time = self.down_open_sell_wait_time

            # 动态止盈线
            dynamic_zs_line = -1
            # 静态止盈线
            static_zs_line = -1
            row_id = self.row_id

            if dynamic_hc_stop_profit_thres > 0:
                a = ((10 - self.current_max_increase * 100) * dynamic_hc_stop_profit_thres) / 100
                a = max(a, 0.004)
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

            # logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 动态止盈线: {dynamic_zs_line:.2f}, 静态止盈线: {static_zs_line:.2f}, 止损线: {zs_line:.2f}")

            if self.current_tick_steps < cold_start_steps:
                return False, self.current_price
            elif self.current_tick_steps == cold_start_steps:
                
                if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                    self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                    monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                    self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                    monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                    self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                    monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                    self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                    monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")

                if self.current_price <= self.avg_price:
                    self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                    stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")
                else:
                    self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                    stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")

                self.running_monitor_down_status[row_id] = False
                self.running_monitor_observe_steps[row_id] = 0
                self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_down_status 更新为 {self.running_monitor_down_status[row_id]}")
                self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_observe_steps 更新为 {self.running_monitor_observe_steps[row_id]}")

            elif self.current_tick_steps > cold_start_steps:
                if self.current_tick_steps % per_step_tick_gap == 0:
                    # 低开低走
                    if self.running_monitor_status[row_id] == constants.StockStatus.DOWN_LOW_AVG_DOWN:
                        
                        if self.smooth_current_price < zs_line and self.smooth_current_price <= self.avg_price:
                            if self.limit_down_status:
                                self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                            else:
                                if self.current_tick_steps < max_abserve_tick_steps:
                                    
                                    # 5min内增加一定的容忍性
                                    
                                    if self.smooth_current_price < self.ma5 and self.open_price > self.ma5:
                                        
                                        self.logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                                else:
                                    self.logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                        # 均线下
                        if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                            
                            if self.smooth_current_price <= self.avg_price:
                                if self.running_monitor_down_status[row_id]:
                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                        self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                        if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                            self.logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price
                                else:
                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                        self.logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                pass
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP

                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                        elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                            if self.smooth_current_price < zs_line and self.smooth_current_price <= self.avg_price:
                                if self.limit_down_status:
                                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                                else:
                                    if self.current_tick_steps < max_abserve_tick_steps:
                                        # 5min内增加一定的容忍性
                                        if self.smooth_current_price < self.ma5:
                                            
                                            self.logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price
                                    else:
                                        self.logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN

                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                    self.logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                                if static_zs_line > 0 and self.current_price <= static_zs_line:
                                    self.logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                    self.logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                                if static_zs_line > 0 and self.current_price <= static_zs_line:
                                    self.logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0

                    elif self.running_monitor_status[row_id] == constants.StockStatus.DOWN_HIGH_AVG_UP:
                        
                        if self.smooth_current_price < zs_line and self.smooth_current_price <= self.avg_price:
                            if self.limit_down_status:
                                self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                            else:
                                if self.current_tick_steps < max_abserve_tick_steps:
                                    # 5min内增加一定的容忍性
                                    if self.smooth_current_price < self.ma5 and self.open_price > self.ma5:
                                        
                                        self.logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                                else:
                                    self.logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                        if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                    self.logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                                if static_zs_line > 0 and self.current_price <= static_zs_line:
                                    self.logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                    self.logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                                if static_zs_line > 0 and self.current_price <= static_zs_line:
                                    self.logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                        elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                            if self.current_price <= self.avg_price:
                                if self.running_monitor_down_status[row_id]:
                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                        self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                        if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                            self.logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price
                                else:
                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                        self.logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                            
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                    elif self.running_monitor_status[row_id] == constants.StockStatus.UP_LOW_AVG_DOWN:

                        if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                            if self.smooth_current_price <=  max(self.last_close_price * (1 + last_close_price_hc_pct), self.open_price * (1 + open_price_max_hc)):
                                self.logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                #     self.sell()
                                #     continue
                                # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                #     self.sell()
                                #     continue
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                        elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                            if self.smooth_current_price <=  max(self.last_close_price * (1 + last_close_price_hc_pct), self.open_price * (1 + open_price_max_hc)):
                                self.logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price

                            if self.current_price <= self.avg_price:
                                if self.open_price > self.avg_price:
                                    
                                    if self.running_monitor_down_status[row_id]:
                                        if self.current_tick_steps >= max_abserve_tick_steps:
                                            self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                            if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                self.logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                return True, self.current_price
                                    else:
                                        if self.current_tick_steps >= max_abserve_tick_steps:
                                            self.logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price

                                else:
                                    if self.current_price <= self.open_price * (1 + last_open_price_hc_pct) and (self.current_tick_steps >= max_abserve_tick_steps or not down_open_sell_wait_time):

                                        self.logger.info(f"跌破开盘价卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                            
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                    elif self.running_monitor_status[row_id] == constants.StockStatus.UP_HIGH_AVG_UP:
                        
                        if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                            if self.smooth_current_price <=  max(self.last_close_price * (1 + last_close_price_hc_pct), self.open_price * (1 + open_price_max_hc)):
                                self.logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                #     self.sell()
                                #     continue
                                # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                #     self.sell()
                                #     continue
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                        elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                            if self.smooth_current_price <=  max(self.last_close_price * (1 + last_close_price_hc_pct), self.open_price * (1 + open_price_max_hc)):
                                self.logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price

                            if self.current_price <= self.avg_price:
                                if self.open_price > self.avg_price:
                                    
                                    if self.running_monitor_down_status[row_id]:
                                        if self.current_tick_steps >= max_abserve_tick_steps:
                                            self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                            if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                self.logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                return True, self.current_price
                                    else:
                                        if self.current_tick_steps >= max_abserve_tick_steps:
                                            self.logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price

                                else:
                                    if self.current_price <= self.open_price * (1 + last_open_price_hc_pct) and (self.current_tick_steps >= max_abserve_tick_steps or not down_open_sell_wait_time):
                                        self.logger.info(f"跌破均价线，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                            
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                            
                # now = datetime.datetime.now().time()
                # target_time = datetime.time(11, 25)
                # if now > target_time:
                #     logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 超过最大时间卖出")
                #     self.add_to_sell(row_id=row_id)
                
        elif self.monitor_type == constants.STOP_LOSS_TRADE_TYPE:
            strategy_name = self.strategy_name
            trade_price = self.trade_price
            limit_down_price = self.limit_down_price
            limit_up_price = self.limit_up_price

            per_step_tick_gap = self.loss_per_step_tick_gap
            cold_start_steps = self.loss_cold_start_steps
            max_abserve_tick_steps = self.loss_max_abserve_tick_steps

            max_abserce_avg_price_down_steps = self.loss_max_abserce_avg_price_down_steps
            
            dynamic_hc_stop_profit_thres = self.loss_dynamic_hc_stop_profit_thres
            static_hc_stop_profit_pct = self.loss_static_hc_stop_profit_pct
            last_close_price_hc_pct = self.loss_last_close_price_hc_pct
            last_open_price_hc_pct = self.loss_last_open_price_hc_pct
            open_price_max_hc = self.loss_open_price_max_hc
            down_open_sell_wait_time = self.loss_down_open_sell_wait_time

            row_id = self.row_id
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

            # logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 动态止盈线: {dynamic_zs_line:.2f}, 静态止盈线: {static_zs_line:.2f}")

            if self.current_tick_steps < cold_start_steps:
                return False, self.current_price
            elif self.current_tick_steps == cold_start_steps:
                
                if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                    self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                    monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                    self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                    monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                    self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                    monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                    self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                    monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")

                if self.current_price <= self.avg_price:
                    self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                    stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")
                else:
                    self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                    stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[row_id]][0]
                    self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")

                if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                    if not self.limit_down_status:
                        # 直接割
                        self.logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                        return True, self.current_price

                self.running_monitor_down_status[row_id] = False
                self.running_monitor_observe_steps[row_id] = 0
                self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_down_status 更新为 {self.running_monitor_down_status[row_id]}")
                self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_observe_steps 更新为 {self.running_monitor_observe_steps[row_id]}")
                return False, self.current_price

            elif self.current_tick_steps > cold_start_steps:
                if self.current_tick_steps % per_step_tick_gap == 0:
                    if self.running_monitor_status[row_id] == constants.StockStatus.DOWN_LOW_AVG_DOWN:
                        if self.smooth_current_price <= self.open_price and self.smooth_current_price <= self.avg_price:
                            if not self.limit_down_status:
                                # 直接割
                                self.logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price
                        
                        if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                            
                            if self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                    self.logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                                if static_zs_line > 0 and self.current_price <= static_zs_line:
                                    self.logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                
                                if self.running_monitor_down_status[row_id]:
                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                        self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                        if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                            self.logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price
                                else:
                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                        self.logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                                
                        elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                            
                            if self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                    self.logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                                if static_zs_line > 0 and self.current_price <= static_zs_line:
                                    self.logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                            else:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0

                    elif self.running_monitor_status[row_id] == constants.StockStatus.DOWN_HIGH_AVG_UP:
                        if self.smooth_current_price <= self.open_price and self.smooth_current_price <= self.avg_price:

                            if not self.limit_down_status:
                                # 直接割
                                self.logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price
                        if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                            if self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                    self.logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                                if static_zs_line > 0 and self.current_price <= static_zs_line:
                                    self.logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                    return True, self.current_price
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                            else:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                        elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                            if self.current_price <= self.avg_price:
                                if self.running_monitor_down_status[row_id]:
                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                        self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                        if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                            self.logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price
                                else:
                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                        self.logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                            if self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP

                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                            else:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                    elif self.running_monitor_status[row_id] == constants.StockStatus.UP_LOW_AVG_DOWN:
                        
                        if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                            if self.smooth_current_price <=  max(self.last_close_price * (1 + last_close_price_hc_pct), self.open_price * (1 + open_price_max_hc)):
                                self.logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                #     self.sell()
                                #     continue
                                # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                #     self.sell()
                                #     continue
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                        elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                            if self.smooth_current_price <=  max(self.last_close_price * (1 + last_close_price_hc_pct), self.open_price * (1 + open_price_max_hc)):
                                self.logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price

                            if self.current_price <= self.avg_price:
                                if self.open_price > self.avg_price:
                                    
                                    if self.running_monitor_down_status[row_id]:
                                        if self.current_tick_steps >= max_abserve_tick_steps:
                                            self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                            if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                self.logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                return True, self.current_price
                                    else:
                                        if self.current_tick_steps >= max_abserve_tick_steps:
                                            self.logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price
                                else:
                                    if self.smooth_current_price <= self.open_price * (1 + last_open_price_hc_pct) and (self.current_tick_steps >= max_abserve_tick_steps or not down_open_sell_wait_time):
                                        self.logger.info(f"跌破开盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                            
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                    elif self.running_monitor_status[row_id] == constants.StockStatus.UP_HIGH_AVG_UP:
                        
                        if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                            if self.smooth_current_price <=  max(self.last_close_price * (1 + last_close_price_hc_pct), self.open_price * (1 + open_price_max_hc)):
                                self.logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                # if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                #     logger.info(f"dynamic stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                #     self.sell()
                                #     continue
                                # if static_zs_line > 0 and self.current_price <= static_zs_line:
                                #     logger.info(f"static stop profit sell. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                #     self.sell()
                                #     continue
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                self.running_monitor_down_status[row_id] = True
                                self.running_monitor_observe_steps[row_id] = 0
                        elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                            if self.smooth_current_price <=  max(self.last_close_price * (1 + last_close_price_hc_pct), self.open_price * (1 + open_price_max_hc)):
                                self.logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                return True, self.current_price

                            if self.current_price <= self.avg_price:
                                if self.open_price > self.avg_price:
                                    
                                    if self.running_monitor_down_status[row_id]:
                                        if self.current_tick_steps >= max_abserve_tick_steps:
                                            self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                            if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                self.logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                return True, self.current_price
                                    else:
                                        if self.current_tick_steps >= max_abserve_tick_steps:
                                            self.logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            return True, self.current_price
                                else:
                                    if self.smooth_current_price <= self.open_price * (1 + last_open_price_hc_pct) and (self.current_tick_steps >= max_abserve_tick_steps or not down_open_sell_wait_time):
                                        self.logger.info(f"跌破开盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                        return True, self.current_price
                            if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                            
                            elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                
                            elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                            elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                    else:
                        return False, self.current_price
            return False, self.current_price

        elif self.monitor_type ==  constants.LAST_TRADE_DAY_TRADE_TYPE:
            strategy_name = self.strategy_name
            trade_price = self.trade_price
            limit_down_price = self.limit_down_price
            limit_up_price = self.limit_up_price
            
            per_step_tick_gap = self.per_step_tick_gap
            cold_start_steps = self.cold_start_steps
            max_abserve_tick_steps = self.max_abserve_tick_steps
            max_abserce_avg_price_down_steps = self.max_abserce_avg_price_down_steps
            last_day_sell_thres = self.last_day_sell_thres
            last_day_sell_huiche = self.last_day_sell_huiche
            max_thres_line = self.smooth_current_max_price * (1 - last_day_sell_huiche)
            if self.current_increase > last_day_sell_thres and self.current_price < max_thres_line:
                self.logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 回撤卖出")
                return True, self.current_price
            return False, self.current_price

        else:
            return False, self.current_price