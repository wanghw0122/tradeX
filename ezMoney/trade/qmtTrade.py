import pprint
import re
import time, sys
from arrow import get
from numpy import true_divide
from xtquant import xttrader
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
from multiprocessing import Manager
import multiprocessing

import sys

sys.path.append(r"D:\workspace\TradeX\ezMoney")

from date_utils import *
from sqlite_processor.mysqlite import SQLiteManager

from logger import logger, order_logger



class MyXtQuantTraderCallback(XtQuantTraderCallback):

    def __init__(self):
        self.qmt = None

    def set_qmt(self, qmt):
        self.qmt = qmt
    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        order_logger.error("连接断开回调")
        logger.error("连接断开回调")

    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        logger.info(f"委托回调 投资备注 {order_id}")

    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        order_id = trade.order_id
        if order_id in self.qmt.orders_dict:
            (stock_code, price, volume, order_type, order_remark, time_stemp, buffered) = self.qmt.orders_dict[order_id]
            traded_amount = trade.traded_amount
            traded_volume = trade.traded_volume
            trade_order_remark = trade.order_remark
            trade_stock_code = trade.stock_code
            trade_order_type = trade.order_type
            traded_price = trade.traded_price
            traded_time = trade.traded_time

            if traded_volume > 0:
                order_logger.info(f"成交回调后实际：订单号 {order_id} 投资备注 {trade_order_remark} 股票代码 {trade_stock_code} 委托方向 {trade_order_type} 成交价格 {traded_price} 成交数量 {traded_volume} 成交金额 {traded_amount} 成交时间 {traded_time}")
                order_logger.info(f"成交前订单申报：订单号 {order_id} 投资备注 {order_remark} 股票代码 {stock_code} 委托类型 {order_type} 委托价格 {price} 委托数量 {volume}  委托时间 {time_stemp} 价格差异 {traded_price - price} 滑点比例 {(traded_price - price) / price} 成交数量 {traded_volume}")
        order_logger.info(f"成交回调: {trade.order_remark}, {trade.stock_code} 委托方向(48买 49卖) {trade.offset_flag} 成交价格 {trade.traded_price} 成交数量 {trade.traded_volume}")

    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        order_id = order_error.order_id
        order_logger.error(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")
        logger.error(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        order_logger.error(f"撤单报错回调 {cancel_error.order_id} {cancel_error.error_msg}")
        logger.error(f"撤单报错回调 {cancel_error.order_id} {cancel_error.error_msg}")

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        order_id = response.order_id
        seq = response.seq
        (stock_code, price, volume, order_type, order_remark) = self.qmt.seq_ids_dict[seq]
        if order_id < 0:
            order_logger.error(f"异步委托失败，股票代码: {stock_code}, 委托价格: {price}, 委托数量: {volume}")
            logger.error(f"异步委托失败，股票代码: {stock_code}, 委托价格: {price}, 委托数量: {volume}")
        else:
            order_logger.info(f"异步委托成功，股票代码: {stock_code}, 委托价格: {price}, 委托数量: {volume}")
            logger.info(f"异步委托成功，股票代码: {stock_code}, 委托价格: {price}, 委托数量: {volume}")
            self.qmt.orders.append(order_id)
            self.qmt.orders_dict[order_id] = (stock_code, price, volume, order_type, order_remark, time.time(), False)
        logger.info(f"异步委托回调 投资备注: {response.order_remark}")


    def on_cancel_order_stock_async_response(self, response):
        """
        :param response: XtCancelOrderResponse 对象
        :return:
        """
        order_id = response.order_id
        cancel_result = response.cancel_result
        orders_dict = self.qmt.orders_dict
        cancel_orders = self.qmt.cancel_orders
        if cancel_result == 0:
            self.qmt.add_cancel_order(order_id)
            order_logger.info(f" order_id {order_id} cancelled result {cancel_result} order_info {orders_dict[order_id]} cancel_orders: {cancel_orders}")


    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        order_logger.info(sys._getframe().f_code.co_name)
        logger.info(sys._getframe().f_code.co_name)


# def create_trader(xt_acc,path, session_id):
#     trader = XtQuantTrader(path, session_id,callback=MyXtQuantTraderCallback())
#     trader.start()
#     connect_result = trader.connect()
#     trader.subscribe(xt_acc)
#     return trader if connect_result == 0 else None


# def try_connect(xt_acc,path):
#     session_id_range = [i for i in range(100, 120)]

#     import random
#     random.shuffle(session_id_range)

#     # 遍历尝试session_id列表尝试连接
#     for session_id in session_id_range:
#         trader = create_trader(xt_acc,path, session_id)
#         if trader:
#             print('连接成功，session_id:{}', session_id)
#             return trader
#         else:
#             print('连接失败，session_id:{}，继续尝试下一个id', session_id)
#             continue

#     print('所有id都尝试后仍失败，放弃连接')
#     return None


# def get_xttrader(xt_acc,path):
#     xt_trader = try_connect(xt_acc,path)
#     return xt_trader

class QMTTrader:
    def __init__(self, path, acc_id):
        logger.info('初始化QMTTrader')
        self.acc = StockAccount(acc_id, 'STOCK')
        self.callback = MyXtQuantTraderCallback()
        # self.callback.qmt = self
        self.trader = self.get_xttrader(path)
        if not self.trader:
            logger.error('QMT未启动，交易接口连接失败, 退出执行.')
            raise Exception('QMT交易接口连接失败')
        else:
            logger.info('QMT交易接口连接成功')
        self.all_stocks = {}
        self.build_all_stocks()
        self.sell_stock_infos = {}

    def init_order_context(self, flag= True):
        manager = Manager()
        if flag:
            self.orders_dict = {}
            self.orders = []
            self.seq_ids_dict = {}
        else:
            self.orders = manager.list()
            self.seq_ids_dict = manager.dict()
            self.orders_dict = manager.dict()
        self.cancel_orders = manager.list()
        self.lock = multiprocessing.Lock()
        self.canceled_orders = []

    def start_sell_listener(self):
        import threading
        self.monitor_thread = threading.Thread(target=self.monitor_sell_stock_infos)
        self.monitor_thread.setDaemon(True)
        self.monitor_thread.start()

    def monitor_sell_stock_infos(self):
        """
        监听 sell_stock_infos 字典的变化
        """
        import json
        db_name = r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db'
        is_trade_day, _ = date.is_trading_day()
        if not is_trade_day:
            return
        monning = date.is_after_920() and not date.is_after_1300()
        afternoon = date.is_after_1300()

        # self.sell_stock_infos[order_id] = (stock_code, left_volume, trade_price, o_id, strategy_name, trade_day, reason, volume)
        if afternoon:
            updated_oids = []
            while True:
                if date.is_after_1505() and len(self.sell_stock_infos) > 0:
                    logger.info(f"sell_stock_infos 发生变化: {self.sell_stock_infos}")
                    cur_orders_stats = self.get_all_orders(filter_order_ids = list(self.sell_stock_infos.keys()))
                    for order_id, info in self.sell_stock_infos.items():
                        stock_code = info[0]
                        left_volume = info[1]
                        trade_price = info[2]
                        o_id = info[3]
                        strategy_name = info[4]
                        trade_day = info[5]
                        reason = info[6]
                        volume = info[7]
                        if order_id not in cur_orders_stats:
                            print(f"order_id {order_id} not in cur_orders_stats")
                            continue
                        cur_order_stat = cur_orders_stats[order_id]
                        order_status = cur_order_stat['order_status']
                        if cur_order_stat['order_status'] == xtconstant.ORDER_PART_SUCC or cur_order_stat['order_status'] == xtconstant.ORDER_SUCCEEDED:
                            traded_price = cur_order_stat['traded_price']
                            traded_volume = cur_order_stat['traded_volume']
                            order_volume = cur_order_stat['order_volume']
                            profit = (traded_price - trade_price) * traded_volume
                            profit_pct = profit / (traded_volume * trade_price)
                            order_logger.info(f"order_id {order_id} sell success, stock_code {stock_code}, status {order_status}, left_volume {left_volume}, o_id {o_id}, strategy_name {strategy_name}, reason {reason}, volume {volume}, traded_price {traded_price}, traded_volume {traded_volume}")
                            volume = 0 if volume <= traded_volume else volume - traded_volume
                            with SQLiteManager(db_name) as manager:
                                manager.update_data("trade_data", {'profit': profit, 'profit_pct': profit_pct, 'left_volume': volume}, {'order_id': o_id})
                                updated_oids.append(o_id)
                        else:
                            order_logger.info(f"order_id {order_id} sell failed, status {order_status}")
                            updated_oids.append(o_id)
                            
                    break
                else:
                    time.sleep(30)

            if updated_oids:
                order_logger.info(f"准备收益和预算更新，更新ids {updated_oids}")
                strategy_to_profits = {}
                strategy_to_logs = {}
                # 更新收益和预算
                with SQLiteManager(db_name) as manager:
                    for oid in updated_oids:
                        trade_infos = manager.query_data_dict("trade_data", {'order_id': oid})
                        if trade_infos:
                            trade_info = trade_infos[0]
                            date_key = trade_info['date_key']
                            stock_code = trade_info['stock_code']
                            strategy_name = trade_info['strategy_name']
                            sub_strategy_name = trade_info['sub_strategy_name']
                            if sub_strategy_name:
                                strategy_name = f"{strategy_name}:{sub_strategy_name}"
                            profit = trade_info['profit']
                            profit_pct = trade_info['profit_pct']
                            left_volume = trade_info['left_volume']
                            if left_volume > 0:
                                order_logger.info(f"left_volume > 0, 不更新收益和预算 {left_volume}")
                                continue

                            profit_info = {
                                "date": date_key,
                                "stock_code": stock_code,
                                "profit": profit,
                                "profit_pct": profit_pct
                            }
                            if strategy_name not in strategy_to_logs:
                                strategy_to_logs[strategy_name] = []
                            if strategy_name not in strategy_to_profits:
                                strategy_to_profits[strategy_name] = 0
                            strategy_to_logs[strategy_name].append(profit_info)
                            strategy_to_profits[strategy_name] = strategy_to_profits[strategy_name] + profit
                    for strategy_name, profit_infos in strategy_to_logs.items():
                            sub_strategy_name = ''
                            if ':' in strategy_name:
                                sub_strategy_name = strategy_name.split(':')[1]
                                query_strategy_name = strategy_name.split(':')[0]
                                strategy_meta_infos = manager.query_data_dict("strategy_meta_info", {'strategy_name': query_strategy_name, 'sub_strategy_name': sub_strategy_name})
                            else:
                                strategy_meta_infos = manager.query_data_dict("strategy_meta_info", {'strategy_name': strategy_name})
                            if not strategy_meta_infos:
                                raise
                            strategy_meta_info = strategy_meta_infos[0]
                            win_delta_budget = strategy_meta_info['win_delta_budget']
                            budget = strategy_meta_info['budget']
                            loss_delta_budget = strategy_meta_info['loss_delta_budget']
                            win_budget_alpha = strategy_meta_info['win_budget_alpha']
                            loss_budget_alpha = strategy_meta_info['loss_budget_alpha']
                            profit_loss_log = strategy_meta_info['profit_loss_log']
                            budget_change_log = strategy_meta_info['budget_change_log']
                            total_profit = strategy_meta_info['total_profit']

                            try:
                                profit_loss_log_json = json.loads(profit_loss_log) if profit_loss_log else []
                            except json.JSONDecodeError:
                                profit_loss_log_json = []

                            try:
                                budget_change_log_json = json.loads(budget_change_log) if budget_change_log else []
                            except json.JSONDecodeError:
                                budget_change_log_json = []
                            
                            profit_loss_log_json.extend(profit_infos)
                            cur_day_profit = strategy_to_profits[strategy_name] if strategy_name in strategy_to_profits else 0
                            if cur_day_profit > 0:
                                add_profit = win_delta_budget + win_budget_alpha * cur_day_profit
                                budget = budget + add_profit
                                order_logger.info(f"收益大于0 要更新总预算 {strategy_name} - {cur_day_profit} - 更新加预算 {add_profit}")
                                budget_change_log_json.append({
                                    "date": date_key,
                                    "add_budget": add_profit,
                                    "timetag": "afternoon"
                                })
                            elif cur_day_profit < 0:
                                add_profit = loss_delta_budget + loss_budget_alpha * cur_day_profit
                                budget = budget + add_profit
                                order_logger.info(f"收益小于0 要更新总预算 {strategy_name} - {cur_day_profit} - 更新减预算 {add_profit}")
                                budget_change_log_json.append({
                                    "date": date_key,
                                    "add_budget": add_profit,
                                    "timetag": "afternoon"
                                })
                            budget_change_log_json_str = json.dumps(budget_change_log_json)
                            profit_loss_log_json_str = json.dumps(profit_loss_log_json)
                            total_profit = total_profit + cur_day_profit

                            if ':' in strategy_name:
                                sub_strategy_name = strategy_name.split(':')[1]
                                query_strategy_name = strategy_name.split(':')[0]
                                manager.update_data("strategy_meta_info", {'profit_loss_log': profit_loss_log_json_str, 'budget': budget, 'budget_change_log': budget_change_log_json_str, 'total_profit': total_profit}, {'strategy_name': query_strategy_name,'sub_strategy_name': sub_strategy_name})
                            else:
                                manager.update_data("strategy_meta_info", {'profit_loss_log': profit_loss_log_json_str, 'budget': budget, 'budget_change_log': budget_change_log_json_str, 'total_profit': total_profit}, {'strategy_name': strategy_name})
        if monning:
            updated_ids = []
            updated_oids = []
            while True:
                if date.is_before_0930():
                    time.sleep(1)
                    continue

                if len(self.sell_stock_infos) <= 0 or date.is_after_0935():
                    order_logger.info("无监听卖出/任务执行完毕，结束任务")
                    order_logger.info(f"准备收益和预算更新，更新ids {updated_oids}")
                    if not updated_oids:
                        break
                    strategy_to_profits = {}
                    strategy_to_logs = {}
                    # 更新收益和预算
                    with SQLiteManager(db_name) as manager:
                        for oid in updated_oids:
                            trade_infos = manager.query_data_dict("trade_data", {'order_id': oid})
                            if trade_infos:
                                trade_info = trade_infos[0]
                                date_key = trade_info['date_key']
                                stock_code = trade_info['stock_code']
                                strategy_name = trade_info['strategy_name']
                                sub_strategy_name = trade_info['sub_strategy_name']
                                if sub_strategy_name:
                                    strategy_name = f"{strategy_name}:{sub_strategy_name}"
                                profit = trade_info['profit']
                                profit_pct = trade_info['profit_pct']
                                left_volume = trade_info['left_volume']
                                if left_volume > 0:
                                    continue

                                profit_info = {
                                    "date": date_key,
                                    "stock_code": stock_code,
                                    "profit": profit,
                                    "profit_pct": profit_pct
                                }
                                if strategy_name not in strategy_to_logs:
                                    strategy_to_logs[strategy_name] = []
                                if strategy_name not in strategy_to_profits:
                                    strategy_to_profits[strategy_name] = 0
                                strategy_to_logs[strategy_name].append(profit_info)
                                strategy_to_profits[strategy_name] = strategy_to_profits[strategy_name] + profit
                        for strategy_name, profit_infos in strategy_to_logs.items():
                            if ':' in strategy_name:
                                sub_strategy_name = strategy_name.split(':')[1]
                                query_strategy_name = strategy_name.split(':')[0]
                                strategy_meta_infos = manager.query_data_dict("strategy_meta_info", {'strategy_name': query_strategy_name,'sub_strategy_name': sub_strategy_name})
                            else:
                                strategy_meta_infos = manager.query_data_dict("strategy_meta_info", {'strategy_name': strategy_name})
                            if not strategy_meta_infos:
                                raise
                            strategy_meta_info = strategy_meta_infos[0]
                            win_delta_budget = strategy_meta_info['win_delta_budget']
                            budget = strategy_meta_info['budget']
                            loss_delta_budget = strategy_meta_info['loss_delta_budget']
                            win_budget_alpha = strategy_meta_info['win_budget_alpha']
                            loss_budget_alpha = strategy_meta_info['loss_budget_alpha']
                            profit_loss_log = strategy_meta_info['profit_loss_log']
                            budget_change_log = strategy_meta_info['budget_change_log']
                            total_profit = strategy_meta_info['total_profit']

                            try:
                                profit_loss_log_json = json.loads(profit_loss_log) if profit_loss_log else []
                            except json.JSONDecodeError:
                                profit_loss_log_json = []

                            try:
                                budget_change_log_json = json.loads(budget_change_log) if budget_change_log else []
                            except json.JSONDecodeError:
                                budget_change_log_json = []
                            
                            profit_loss_log_json.extend(profit_infos)
                            cur_day_profit = strategy_to_profits[strategy_name] if strategy_name in strategy_to_profits else 0
                            if cur_day_profit > 0:
                                add_profit = win_delta_budget + win_budget_alpha * cur_day_profit
                                budget = budget + add_profit
                                order_logger.info(f"收益大于0 要更新总预算 {strategy_name} - {cur_day_profit} - 更新加预算 {add_profit}")
                                budget_change_log_json.append({
                                    "date": date_key,
                                    "add_budget": add_profit,
                                    "timetag": "moning"
                                })
                            elif cur_day_profit < 0:
                                add_profit = loss_delta_budget + loss_budget_alpha * cur_day_profit
                                budget = budget + add_profit
                                order_logger.info(f"收益小于0 要更新总预算 {strategy_name} - {cur_day_profit} - 更新减预算 {add_profit}")
                                budget_change_log_json.append({
                                    "date": date_key,
                                    "add_budget": add_profit,
                                    "timetag": "moning"
                                })
                            budget_change_log_json_str = json.dumps(budget_change_log_json)
                            profit_loss_log_json_str = json.dumps(profit_loss_log_json)
                            total_profit = total_profit + cur_day_profit
                            if ':' in strategy_name:
                                sub_strategy_name = strategy_name.split(':')[1]
                                query_strategy_name = strategy_name.split(':')[0]
                                manager.update_data("strategy_meta_info", {'profit_loss_log': profit_loss_log_json_str, 'budget': budget, 'budget_change_log': budget_change_log_json_str, 'total_profit': total_profit}, {'strategy_name': query_strategy_name,'sub_strategy_name': sub_strategy_name})
                            else:
                                manager.update_data("strategy_meta_info", {'profit_loss_log': profit_loss_log_json_str, 'budget': budget, 'budget_change_log': budget_change_log_json_str, 'total_profit': total_profit}, {'strategy_name': strategy_name})

                    break
                order_logger.info(f"监听卖出，任务执行。 {self.sell_stock_infos}")
                cur_orders_stats = self.get_all_orders(filter_order_ids = list(self.sell_stock_infos.keys()))
                keys_to_delete = []
                kv_to_merge = {}
                for order_id, info in self.sell_stock_infos.items():
                    stock_code = info[0]
                    left_volume = info[1]
                    trade_price = info[2]
                    o_id = info[3]
                    strategy_name = info[4]
                    trade_day = info[5]
                    reason = info[6]
                    volume = info[7]
                    if order_id not in cur_orders_stats:
                        continue

                    cur_order_stat = cur_orders_stats[order_id]
                    order_status = cur_order_stat['order_status']
                    if order_status == xtconstant.ORDER_SUCCEEDED:
                        
                        traded_price = cur_order_stat['traded_price']
                        traded_volume = cur_order_stat['traded_volume']
                        order_volume = cur_order_stat['order_volume']
                        profit = (traded_price - trade_price) * traded_volume
                        profit_pct = profit / (traded_volume * trade_price)

                        volume = 0 if volume <= traded_volume else volume - traded_volume
                        with SQLiteManager(db_name) as manager:
                            if order_id in updated_ids:
                                manager.update_data("trade_data", {'profit': profit, 'profit_pct': profit_pct, 'left_volume': volume}, {'order_id': o_id})
                            else:
                                origin_dct = manager.query_data_dict("trade_data", {'order_id': o_id})
                                origin_profit = 0
                                origin_profit_pct = profit_pct
                                if origin_dct:
                                    origin_dct = origin_dct[0]
                                    origin_profit = origin_dct['profit']
                                    if origin_profit < -0.99:
                                        origin_profit = 0
                                    origin_profit_pct = origin_dct['profit_pct']
                                    if origin_profit_pct < -0.99:
                                        origin_profit_pct = profit_pct
                                manager.update_data("trade_data", {'profit': profit + origin_profit, 'profit_pct': (profit_pct + origin_profit_pct) / 2, 'left_volume': volume}, {'order_id': o_id})
                        if order_id not in updated_ids:
                            updated_ids.append(order_id)
                        if o_id not in updated_oids:
                            updated_oids.append(o_id)
                        keys_to_delete.append(order_id)
                    elif order_status == xtconstant.ORDER_PART_CANCEL or order_status == xtconstant.ORDER_CANCELED:
                        traded_price = cur_order_stat['traded_price']
                        traded_volume = cur_order_stat['traded_volume']
                        order_volume = cur_order_stat['order_volume']

                        if traded_volume > 0 and order_id not in updated_ids:
                            profit = (traded_price - trade_price) * traded_volume
                            profit_pct = profit / (traded_volume * trade_price)

                            volume = 0 if volume <= traded_volume else volume - traded_volume
                            with SQLiteManager(db_name) as manager:
                                origin_dct = manager.query_data_dict("trade_data", {'order_id': o_id})
                                origin_profit = 0
                                origin_profit_pct = profit_pct
                                if origin_dct:
                                    origin_dct = origin_dct[0]
                                    origin_profit = origin_dct['profit']
                                    if origin_profit < -0.99:
                                        origin_profit = 0
                                    origin_profit_pct = origin_dct['profit_pct']
                                    if origin_profit_pct < -0.99:
                                        origin_profit_pct = profit_pct
                                manager.update_data("trade_data", {'profit': profit + origin_profit, 'profit_pct': (profit_pct + origin_profit_pct) / 2, 'left_volume': volume}, {'order_id': o_id})
                            if order_id not in updated_ids:
                                updated_ids.append(order_id)
                            if o_id not in updated_oids:
                                updated_oids.append(o_id)

                        l_volume = order_volume - traded_volume
                        if l_volume <= 0:
                            keys_to_delete.append(order_id)
                            continue
                        full_tick_info = xtdata.get_full_tick([stock_code])
                        if not full_tick_info or stock_code not in full_tick_info:
                            print(f"stock_code {stock_code} not in full_tick_info")
                            continue
                        lastPrice = full_tick_info[stock_code]['lastPrice']
                        sell_price = lastPrice
                        if 'bidPrice' in full_tick_info[stock_code]:
                            bidPrice = full_tick_info[stock_code]['bidPrice']
                            if len(bidPrice) and bidPrice[0] > 0:
                                sell_price = bidPrice[0]
                        if 'max_days' in reason:
                            sid = self.sell(stock_code, sell_price, l_volume, order_remark=strategy_name)
                            
                            if sid > 0:
                                kv_to_merge[sid] = (stock_code, left_volume, trade_price, o_id, strategy_name, trade_day, reason, l_volume)
                                keys_to_delete.append(order_id)
                        elif 'take_profit' in reason:
                            take_profit_pct = float(reason.split('|')[1])
                            if lastPrice / trade_price - 1 > take_profit_pct:
                                sid = self.sell(stock_code, sell_price, l_volume, order_remark=strategy_name)
                            
                                if sid > 0:
                                    kv_to_merge[sid] = (stock_code, left_volume, trade_price, o_id, strategy_name, trade_day, reason, l_volume)
                                    keys_to_delete.append(order_id)
                        elif 'stop_loss' in reason:

                            stop_loss_pct = float(reason.split('|')[1])
                            if lastPrice / trade_price - 1 < stop_loss_pct:
                                sid = self.sell(stock_code, sell_price, l_volume, order_remark=strategy_name)
                            
                                if sid > 0:
                                    kv_to_merge[sid] = (stock_code, left_volume, trade_price, o_id, strategy_name, trade_day, reason, l_volume)
                                    keys_to_delete.append(order_id)
                    elif order_status == xtconstant.ORDER_JUNK:
                        keys_to_delete.append(order_id)
                        continue
                    else:
                        self.cancel_order(order_id)

                for key in keys_to_delete:
                    if key in self.sell_stock_infos:
                        del self.sell_stock_infos[key]
                for key, value in kv_to_merge.items():
                    self.sell_stock_infos[key] = value

                time.sleep(5)

    def get_orders_dict(self):
        return self.orders_dict

    def add_cancel_order(self, order_id):
        if order_id in self.canceled_orders:
            return
        with self.lock:
            if order_id not in self.cancel_orders:
                self.cancel_orders.append(order_id)
                self.add_canceled_order(order_id)
    
    def add_canceled_order(self, order_id):
        if order_id in self.canceled_orders:
            logger.error(f"order_id {order_id} already in canceled_orders")
            return
        self.canceled_orders.append(order_id)
    

    def get_all_cancel_order_infos(self):
        order_ids = []
        with self.lock:
            for order_id in self.cancel_orders:
                if order_id not in order_ids:
                    order_ids.append(order_id)
            while self.cancel_orders:
                del self.cancel_orders[0]
        return self.get_all_orders(filter_order_ids=order_ids)


    def build_all_stocks(self):
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        for stock in all_stocks:
            if stock.startswith('60') or stock.startswith('00'):
                code = stock.split('.')[0]
                self.all_stocks[code] = stock
        logger.info(f"构建全市场股票字典完毕。 共{len(self.all_stocks)}个")
    
    def get_xttrader(self, path):
        session_id_range = [i for i in range(100, 120)]
        import random
        random.shuffle(session_id_range)

        # 遍历尝试session_id列表尝试连接
        for session_id in session_id_range:
            trader = XtQuantTrader(path, session_id,callback=self.callback)
            trader.start()
            connect_result = trader.connect()
            if trader and connect_result == 0:
                logger.info(f'连接成功，session_id:{session_id}')
                trader.subscribe(self.acc) 
                return trader
            else:
                logger.info(f'连接失败，session_id:{session_id}，继续尝试下一个id')
                continue
        logger.info('所有id都尝试后仍失败，放弃连接')
        return None

    def buy(self, stock_code, price, volume, order_type=xtconstant.FIX_PRICE, order_remark='', sync = True, orders_dict = None, orders = None, buffered=False):
        """
        买入股票

        :param account: 资金账号
        :param stock_code: 股票代码
        :param price: 买入价格
        :param volume: 买入数量
        :param order_type: 委托类型，默认为固定价格委托
        :param order_remark: 委托备注，默认为空
        :return: 委托ID
        """
        
        from decimal import Decimal, ROUND_HALF_UP
        new_price = float(Decimal(str(price)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
        
        if sync:
            if order_type == xtconstant.FIX_PRICE:
                order_id = self.trader.order_stock(self.acc, stock_code, xtconstant.STOCK_BUY, volume, order_type, new_price, order_remark)
            else:
                order_id = self.trader.order_stock(self.acc, stock_code, xtconstant.STOCK_BUY, volume, order_type, 0, order_remark)
            if order_id < 0:
                order_logger.error(f"委托失败，股票代码: {stock_code}, 委托价格: {new_price}, 委托类型: {order_type}, 委托数量: {volume}, 委托ID: {order_id}")
            else:
                order_logger.info(f"委托成功，股票代码: {stock_code}, 委托价格: {new_price}, 委托类型: {order_type}, 委托数量: {volume}, 委托ID: {order_id}")
                try:
                    from sqlite_processor.mysqlite import SQLiteManager
                    from date_utils import date
                    date_key = date.get_current_date()
                    db_name = r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db'
                    table_name = 'trade_data'
                    
                    with SQLiteManager(db_name) as manager:
                        if order_remark and ':' in order_remark:
                            strategy_name = order_remark.split(':')[0]
                            sub_strategy_name = order_remark.split(':')[1]
                            manager.insert_data(table_name, {'date_key': date_key,'order_id': order_id,'strategy_name': strategy_name, 'sub_strategy_name': sub_strategy_name, 'buy0_or_sell1': 0,'stock_code': stock_code,'order_type': order_type, 'order_price': new_price, 'order_volume': volume})
                        else:
                            manager.insert_data(table_name, {'date_key': date_key,'order_id': order_id, 'strategy_name': order_remark, 'buy0_or_sell1': 0, 'stock_code': stock_code ,'order_type': order_type, 'order_price': new_price, 'order_volume': volume})
                except Exception as e:
                    logger.error(f"插入数据失败 {e}")
                    order_logger.error(f"插入数据失败 {e}")

                if orders_dict != None:
                    orders_dict[order_id] = (stock_code, new_price, volume, order_type, order_remark, time.time(), buffered)
                if orders != None:
                    orders.append(order_id)
            return order_id
        else:
            seq_id = self.trader.order_stock_async(self.acc, stock_code, xtconstant.STOCK_BUY, volume, order_type, new_price, order_remark)
            self.seq_ids_dict[seq_id] = (stock_code, new_price, volume, order_type, order_remark)
            return seq_id


    def sell_quickly(self, stock_code, volume, order_type=xtconstant.FIX_PRICE, order_remark='', sync = True, buffer = 0, extra_info = None):
        """
        卖出股票

        :param account: 资金账号
        :param stock_code: 股票代码
        :param price: 卖出价格
        :param volume: 卖出数量
        :param order_type: 委托类型，默认为固定价格委托
        :param order_remark: 委托备注，默认为空
        :return: 委托ID
        """
        full_tick_info = xtdata.get_full_tick([stock_code])
        if not full_tick_info:
            order_logger.error(f"[出售] 获取股票 {stock_code} 行情失败")
            return
        price = full_tick_info[stock_code]['lastPrice'] * (1 + buffer)
        from decimal import Decimal, ROUND_HALF_UP
        new_price = float(Decimal(str(price)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))

        limit_down_price = 0

        if full_tick_info and 'lastClose' in full_tick_info[stock_code]:
            last_close = full_tick_info[stock_code]['lastClose']
            print(f"last_close {last_close}")
            from decimal import Decimal, ROUND_HALF_UP
            limit_down_price = float(Decimal(str(last_close * 0.9)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
            
        sell_price = max(new_price, limit_down_price)
        
        if sync:
            if order_type == xtconstant.FIX_PRICE:
                order_id = self.trader.order_stock(self.acc, stock_code, xtconstant.STOCK_SELL, volume, order_type, sell_price, order_remark)
            else:
                order_id = self.trader.order_stock(self.acc, stock_code, xtconstant.STOCK_SELL, volume, order_type, 0, order_remark)
            if order_id < 0:
                order_logger.error(f"委托出售失败，股票代码: {stock_code}, 委托价格: {sell_price}, 委托类型: {order_type}, 委托数量: {volume}, 委托ID: {order_id}")
            else:
                order_logger.info(f"委托出售成功，股票代码: {stock_code}, 委托价格: {sell_price}, 委托类型: {order_type}, 委托数量: {volume}, 委托ID: {order_id}")
                try:
                    from sqlite_processor.mysqlite import SQLiteManager
                    from date_utils import date
                    date_key = date.get_current_date()
                    db_name = r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db'
                    table_name = 'trade_data'
                    with SQLiteManager(db_name) as manager:
                        if order_remark and ':' in order_remark:
                            set_strategy_name = order_remark.split(':')[0]
                            sub_strategy_name = order_remark.split(':')[1]
                            manager.insert_data(table_name, {'date_key': date_key,'order_id': order_id,'strategy_name': set_strategy_name,'sub_strategy_name': sub_strategy_name, 'buy0_or_sell1': 1,'stock_code': stock_code,'order_type': order_type, 'order_price': sell_price, 'order_volume': volume})
                        else:
                            manager.insert_data(table_name, {'date_key': date_key,'order_id': order_id, 'strategy_name': order_remark, 'buy0_or_sell1': 1, 'stock_code': stock_code ,'order_type': order_type, 'order_price': sell_price, 'order_volume': volume})
                except Exception as e:
                    order_logger.error(f"插入数据失败 {e}")
                if extra_info:
                
                    stock_code = extra_info[0]
                    left_volume = extra_info[1]
                    trade_price = extra_info[2]
                    o_id = extra_info[3]
                    strategy_name = extra_info[4]
                    trade_day = extra_info[5]
                    reason = extra_info[6]
                    self.sell_stock_infos[order_id] = (stock_code, left_volume, trade_price, o_id, strategy_name, trade_day, reason, volume)

            return order_id
        else:
            seq_id = self.trader.order_stock_async(self.acc, stock_code, xtconstant.STOCK_SELL, volume, order_type, sell_price, order_remark)
            self.seq_ids_dict[seq_id] = (stock_code, sell_price, volume, order_type, order_remark)
            return seq_id



    def buy_quickly(self, stock_code, cash, min_vol = -1, max_vol = -1, max_cash = -1, order_type=xtconstant.FIX_PRICE, order_remark='', sync = True, price_type = 0, orders_dict = None, orders = None, buffers= [0.0]):

        if max_cash > 0:
            cash = min(cash, max_cash)
        if cash <= 0:
            logger.error(f"{stock_code} 买入金额预算不够 {cash}")
            return
        if stock_code in self.all_stocks:
            stock_code = self.all_stocks[stock_code]
        full_tick = xtdata.get_full_tick([stock_code])
        (account_id, account_cash, account_frozen_cash, account_market_value, account_total_asset) = self.get_account_info()
        
        if not full_tick or len(full_tick) == 0:
            logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            return
        elif stock_code not in full_tick:
            logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            return
        elif 'lastPrice' not in full_tick[stock_code]:
            logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            return
        elif 'askPrice' not in full_tick[stock_code]:
            logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            return
        else:
            logger.info(f"{stock_code} 全推行情： {full_tick}")
        
        current_price = full_tick[stock_code]['lastPrice']
        ask_price = full_tick[stock_code]['askPrice']
        bid_price = current_price
        price1 = ask_price[0]
        price2 = ask_price[1]
        price3 = ask_price[2]

        if price_type == 0:
            bid_price = current_price
        elif price_type == 1 and price1 > 0 and price1 > current_price:
            bid_price = price1
        elif price_type == 2 and price2 > 0 and price2 > current_price:
            bid_price = price2
        elif price_type == 3 and price3 > 0 and price3 > current_price:
            bid_price = price3
        else:
            bid_price = current_price

        if bid_price <= 0:
            logger.error(f"price error.： {full_tick}")
            return

        #买入金额 取目标金额 与 可用金额中较小的
        buy_amount = min(account_cash, cash)
        #买入数量 取整为100的整数倍
        buy_vol = int(buy_amount / bid_price / 100) * 100

        if max_vol > 0:
            buy_vol = min(buy_vol, max_vol)
        if min_vol > 0:
            buy_vol = max(buy_vol, min_vol)
        if buy_vol == 0:
            logger.error(f"当前可用资金 {account_cash} 目标买入金额 {cash} 买入股数 {buy_vol}股")
            return
        logger.info(f"当前可用资金 {account_cash} 目标买入金额 {cash} 买入股数 {buy_vol}股")
        if not buffers or len(buffers) == 0:
            id = self.buy(stock_code, bid_price, buy_vol, order_type, order_remark, sync, orders_dict=orders_dict, orders=orders)
            order_logger.info(f"下单买入股票无buffer {stock_code} 买入股数 {buy_vol} 买入金额 {buy_amount} 买入价格 {bid_price} 买入一价 {price1} 买入二价 {price2} 买入三价{price3} 委托ID {id}")
            return id
        else:
            buffers.sort(reverse=True)
            buffer_len = len(buffers)
            vols = []
            every_vol = buy_vol // 100 // buffer_len * 100
            if every_vol == 0:
                buffers.sort(reversed=False)
                all_vol = buy_vol
                for i in range(0, buffer_len):
                    if all_vol < 100:
                        vols.append(0)
                    else:
                        if i == buffer_len - 1:
                            vols.append(all_vol)
                            all_vol = 0
                        else:
                            vols.append(100)
                            all_vol = all_vol - 100
            else:
                all_vol = buy_vol
                for i in range(0, buffer_len):
                    if all_vol < every_vol:
                        vols.append(all_vol)
                        all_vol = 0
                    else:
                        if i == buffer_len - 1:
                            vols.append(all_vol)
                            all_vol = 0
                        else:
                            vols.append(every_vol)
                            all_vol = all_vol - every_vol
            order_logger.info(f"下单买入股票有buffer {stock_code} 买入总股数 {buy_vol} 买入总金额 {buy_amount} 买入buffers {buffers} 买入数量 {vols} 买入最低价格 {bid_price} 买入一价 {price1} 买入二价 {price2} 买入三价{price3}")
            for i in range(0, buffer_len):
                buffer = buffers[i]
                buy_vol_i = vols[i]
                if buy_vol_i > 0:
                    buy_amount = buy_vol_i * bid_price * (1 + buffer)
                    id = self.buy(stock_code, bid_price * (1 + buffer), buy_vol_i, order_type, order_remark, sync, orders_dict=orders_dict, orders=orders, buffered=buffer>0)
                    order_logger.info(f"循环下单买入了股票有buffer {buffer} {stock_code} 买入股数 {buy_vol_i} 买入金额 {buy_amount} 买入价格 {bid_price * (1 + buffer)} 买入buffer {buffer} 委托ID {id}")
        return id

    def sell(self, stock_code, price, volume, order_type=xtconstant.FIX_PRICE, order_remark=''):
        """
        卖出股票

        :param account: 资金账号
        :param stock_code: 股票代码
        :param price: 卖出价格
        :param volume: 卖出数量
        :param order_type: 委托类型，默认为固定价格委托
        :param order_remark: 委托备注，默认为空
        :return: 委托ID
        """
        return self.trader.order_stock(self.acc, stock_code, xtconstant.STOCK_SELL, volume, order_type, price, order_remark)

    def cancel_order(self, order_id, sync = True):
        """
        撤单

        :param account: 资金账号
        :param order_id: 委托ID
        :return: 撤单结果
        """
        order_logger.info(f"准备撤单 订单号 - {order_id}")
        if sync:
            return self.trader.cancel_order_stock(self.acc, order_id)
        return self.trader.cancel_order_stock_async(self.acc, order_id)

    def get_account_info(self):
        """
        获取账户信息

        :return: 账户信息
        """
        account_info = self.trader.query_stock_asset(self.acc)
        account_info_tuple = (account_info.account_id, account_info.cash, account_info.frozen_cash, account_info.market_value, account_info.total_asset)
        logger.info(f"账户ID: {account_info_tuple[0]}, 可用资金: {account_info_tuple[1]}, 冻结资金: {account_info_tuple[2]}, 市值: {account_info_tuple[3]}, 总资产: {account_info_tuple[4]}")
        return account_info_tuple


    def get_position_info(self):
        """
        获取持仓信息

        :param account: 资金账号
        :return: 持仓信息
        """
        return self.trader.query_stock_positions(self.acc)
    


    def query_stock_trades(self):
        """
        查询股票交易信息
        """
        return self.trader.query_stock_trades(self.acc)
    
    
    def get_tradable_stocks(self):
        """
        获取可交易股票数据

        :param account: 资金账号
        :return: 可交易股票数据列表，每个元素为一个字典，包含股票代码和可卖出数量
        """
        tradable_stocks = []

        # 获取账户持仓信息
        positions = self.get_position_info()

        for position in positions:
            stock_code = position.stock_code
            available_qty = position.can_use_volume
            quantity = position.volume

            logger.info(f"股票代码: {stock_code}, 可卖出数量: {available_qty}, 持仓数量: {quantity}")

            tradable_stocks.append({
                'stock_code': stock_code,
                'available_qty': available_qty,
                'quantity': quantity
            })

        return tradable_stocks
    
    def sell_all_holdings(self, order_remark='', filter_codes = []):
        """
        卖出所有持仓股票

        :param account: 资金账号
        :return: 卖出结果
        """
        # now = datetime.datetime.now()
        # if now.hour > 0:
        #     logger.error(f"当前时间 {now} 非0点时间，无法自动卖出")
        #     return
        logger.info(f"开始卖出所有持仓股票")

        hold_positions = self.get_tradable_stocks()
        sell_results = []

        for position in hold_positions:
            stock_code = position['stock_code']
            if stock_code in filter_codes:
                logger.info(f"股票 {stock_code} 在过滤列表中，跳过卖出")
                continue
            quantity = position['available_qty']
            limit_down_price = self.calculate_limit_down_price(stock_code)

            logger.info(f"准备挂单卖出 股票代码: {stock_code}, 可卖出数量: {quantity}, 卖出跌停价: {limit_down_price}")
            if limit_down_price:
                sell_result = self.sell(stock_code, limit_down_price, quantity)
                sell_results.append({
                    'stock_code': stock_code,
                    'quantity': quantity,
                    'sell_price': limit_down_price,
                    'sell_result': sell_result
                })
                # self.seq_ids_dict[sell_result] = (stock_code, limit_down_price, quantity, xtconstant.FIX_PRICE, order_remark)
            else:
                logger.error(f"股票 {stock_code} 的跌停价计算错误，无法卖出")
        return sell_results
    

    def sell_all_holdings_end(self, order_remark='', filter_codes = []):
        """
        卖出所有持仓股票

        :param account: 资金账号
        :return: 卖出结果
        """
        # now = datetime.datetime.now()
        # if now.hour > 0:
        #     logger.error(f"当前时间 {now} 非0点时间，无法自动卖出")
        #     return
        logger.info(f"开始卖出所有持仓股票")

        hold_positions = self.get_tradable_stocks()
        sell_results = []

        for position in hold_positions:
            stock_code = position['stock_code']
            if stock_code in filter_codes:
                logger.info(f"股票 {stock_code} 在过滤列表中，跳过卖出")
                continue
            quantity = position['available_qty']
            down_price = self.calculate_sell_price(stock_code)
            limit_down_price = self.calculate_limit_down_price(stock_code)
            limit_down_price = max(limit_down_price, down_price)

            logger.info(f"准备挂单卖出 股票代码: {stock_code}, 可卖出数量: {quantity}, 卖出跌停价: {limit_down_price}")
            if limit_down_price:
                sell_result = self.sell(stock_code, limit_down_price, quantity)
                sell_results.append({
                    'stock_code': stock_code,
                    'quantity': quantity,
                    'sell_price': limit_down_price,
                    'sell_result': sell_result
                })
                # self.seq_ids_dict[sell_result] = (stock_code, limit_down_price, quantity, xtconstant.FIX_PRICE, order_remark)
            else:
                logger.error(f"股票 {stock_code} 的跌停价计算错误，无法卖出")
        return sell_results
    

    def calculate_sell_price(self, stock_code):
        """
        计算第二天跌停价

        :param stock_code: 股票代码
        :return: 第二天跌停价，如果计算失败则返回 None
        """
        try:
            full_tick = xtdata.get_full_tick([stock_code])
            if full_tick and 'lastPrice' in full_tick[stock_code]:
                last_price = full_tick[stock_code]['lastPrice']
                print(f"last_price {last_price}")
                from decimal import Decimal, ROUND_HALF_UP
                limit_down_price = Decimal(str(last_price * 0.99)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                return limit_down_price
            else:
                logger.error(f"无法获取股票 {stock_code} 的最新价")
                return None
        except Exception as e:
            logger.error(f"计算股票 {stock_code} 的跌停价时发生错误: {e}")
            return None
    
    def calculate_limit_down_price(self, stock_code):
        """
        计算第二天跌停价

        :param stock_code: 股票代码
        :return: 第二天跌停价，如果计算失败则返回 None
        """
        try:
            full_tick = xtdata.get_full_tick([stock_code])
            if full_tick and 'lastPrice' in full_tick[stock_code]:
                last_price = full_tick[stock_code]['lastPrice']
                print(f"last_price {last_price}")
                from decimal import Decimal, ROUND_HALF_UP
                limit_down_price = Decimal(str(last_price * 0.9)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                return limit_down_price
            else:
                logger.error(f"无法获取股票 {stock_code} 的最新价")
                return None
        except Exception as e:
            logger.error(f"计算股票 {stock_code} 的跌停价时发生错误: {e}")
            return None

    
    def set_running(self):
        self.trader.run_forever()
    
    def cancel_active_orders(self):
        """
        撤单所有未成交且可撤单的股票

        :param account: 资金账号
        :return: 撤单结果
        """
        cancel_results = []
        active_orders = self.get_all_orders(cancelable_only  = True)
        for order in active_orders.values():
            order_id = order['order_id']
            cancel_result = self.cancel_order(order_id, sync=False)
            cancel_results.append({
                'order_id': order_id,
                'cancel_result': cancel_result
            })

        return cancel_results
    

    def get_all_orders(self, cancelable_only = False, filter_order_ids = None):
        """
        获取当前委托、未成交且可撤单的股票

        :param account: 资金账号
        :return: 满足条件的委托信息列表，每个元素为一个字典，包含股票代码、委托数量、委托价格等信息
        """
        active_orders = {}

        # 获取账户委托信息
        orders = self.trader.query_stock_orders(self.acc, cancelable_only=cancelable_only)
        for order in orders:
            if filter_order_ids != None and order.order_id not in filter_order_ids:
                continue
            active_orders[order.order_id] = {
                'stock_code': order.stock_code,
                'order_id': order.order_id,
                'order_time': order.order_time,
                'order_volume': order.order_volume,
                'order_type': order.order_type,
                'price': order.price,
                'order_status': order.order_status,
                'strategy_name': order.strategy_name,
                'traded_volume': order.traded_volume,
                'traded_price': order.traded_price,
                'status_msg': order.status_msg
            }

        return active_orders




# 使用示例
if __name__ == '__main__':
    path = r'D:\qmt\userdata_mini'  # QMT客户端路径
    
    acc_id = '8886660057'

    # 创建QMTTrader实例
    qmt_trader = QMTTrader(path, acc_id)

    print("download")
    xtdata.download_history_data('000785.SZ', '1d', start_time='', end_time='20250114')

    # 买入股票
    order_id = qmt_trader.buy_quickly('000785.SZ', 1000, sync=False)
    print(f"买入委托ID: {order_id}")

    

    # # 卖出股票
    # order_id = qmt_trader.sell('600000.SH', 11.0, 50)
    # print(f"卖出委托ID: {order_id}")

    # # 撤单
    # cancel_result = qmt_trader.cancel_order(order_id)
    # print(f"撤单结果: {cancel_result}")

    # 获取账户信息
    # account_info = qmt_trader.get_account_info()
    # print(f"账户信息: {account_info}")

    # get_tradable_stocks = qmt_trader.get_tradable_stocks()
    # print(f"股票数据: {get_tradable_stocks}")

    qmt_trader.set_running()
