from numpy import real
from ezMoney import trade
from trade.qmtTrade import *
import datetime

path = r'D:\qmt\userdata_mini'  # QMT客户端路径
acc_id = '8886660057'
# 创建QMTTrader实例
logger.info("开始初始化QMT....")

qmt_trader = QMTTrader(path, acc_id)
qmt_trader.callback.set_qmt(qmt_trader)
db_name = r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db'



class OfflineStockQuery:
    def __init__(self):
        self.database = None
        self.load_database()
    
    def load_database(self, filepath=r"D:\workspace\TradeX\ezMoney\sqlite_db\stock_database.csv"):
        """加载本地数据库"""
        try:
            self.database = pd.read_csv(filepath, dtype={'代码': str})
            self.database.set_index('代码', inplace=True)
        except FileNotFoundError:
            raise Exception("本地数据库文件不存在，请先运行生成程序")

    def get_stock_name(self, stock_code):
        """通过股票代码查询名称"""
        # 规范输入格式

        prefix = 'sh' if stock_code.startswith(('6', '9')) else 'sz'
        code = f"{prefix}{stock_code}"
        
        try:
            return self.database.loc[code, '名称']
        except KeyError:
            return ''  # 未找到对应代码


offlineStockQuery = OfflineStockQuery()

def schedule_sell_stocks_everyday_at_1457():
    try:
        is_trade, pre_trade_date = date.is_trading_day()
        if not is_trade:
            logger.info("非交易日，不更新预算。")
            return
        last_10_trade_days = date.get_trade_dates_by_end(pre_trade_date, 10)

        if not last_10_trade_days:
            order_logger.info("获取最近10个交易日失败")
            return
        last_10_trade_days.sort()

        position_stocks =  qmt_trader.get_tradable_stocks()

        if not position_stocks:
            order_logger.info("无股票可出售")
            return
        
        selled_codes = []
        all_available_codes = []
        all_available_codes_dict = {}
        for position_stock_info in position_stocks:
            stock_code = position_stock_info['stock_code']
            available_qty = position_stock_info['available_qty']
            quantity = position_stock_info['quantity']
            if available_qty <= 0:
                continue
            all_available_codes.append(stock_code)
            all_available_codes_dict[stock_code] = position_stock_info

        if all_available_codes:
            full_ticks = xtdata.get_full_tick(all_available_codes)
        
            if full_ticks and len(full_ticks):
                for c_stock_code, c_full_tick in full_ticks.items():

                    if c_stock_code not in all_available_codes_dict:
                        continue
                    if 'lastPrice' not in c_full_tick:
                        continue
                    if 'lastClose' not in c_full_tick:
                        continue
                    c_available_qty = all_available_codes_dict[c_stock_code]['available_qty']
                    last_price = c_full_tick['lastPrice']
                    last_close = c_full_tick['lastClose']
                    high = c_full_tick['high']
                    limit_down_price, limit_up_price = constants.get_limit_price(last_close, c_stock_code)

                    print(c_stock_code, c_available_qty, last_price, last_close, limit_up_price, high)
                    if abs(high - limit_up_price) < 0.01 and abs(last_price - limit_up_price) > 0.02:
                        stock_name = offlineStockQuery.get_stock_name(c_stock_code)
                        qmt_trader.sell_quickly(c_stock_code, stock_name, c_available_qty, order_remark= "sell",  buffer=-0.03, extra_infos = None, up_sell=False, afternoon=True)
                        selled_codes.append(c_stock_code)

        if selled_codes:
            # 过滤 position_stocks 列表，保留 stock_code 不在 selled_codes 中的项
            position_stocks = [position_stock_info for position_stock_info in position_stocks if position_stock_info['stock_code'] not in selled_codes]

        if not position_stocks:
            order_logger.info("过滤炸板后无股票可出售")
            return
        else:
            order_logger.info("过滤炸板后有股票可出售")
                        
        stock_to_trade_volume = {}
        days_strategy_to_stock_volume = {}

        for position_stock_info in position_stocks:
            if not position_stock_info:
                continue
            stock_code = position_stock_info['stock_code']
            stock_volume = position_stock_info['available_qty']
            if stock_volume > 0:
                stock_to_trade_volume[stock_code] = stock_volume
        
        for trade_day in last_10_trade_days:
            with SQLiteManager(db_name) as manager:
                trade_day_datas = manager.query_data_dict("trade_data", {"date_key": trade_day, "buy0_or_sell1": 0})
                trade_day_datas = [trade_day_data for trade_day_data in trade_day_datas if trade_day_data['left_volume'] > 0 and trade_day_data['stock_code'] in stock_to_trade_volume]
                if not trade_day_datas:
                    order_logger.info(f"无数据可出售 {trade_day}")
                    continue
                for trade_day_data in trade_day_datas:
                    strategy_name = trade_day_data['strategy_name']
                    sub_strategy_name = trade_day_data['sub_strategy_name']
                    if sub_strategy_name:
                        strategy_name = f"{strategy_name}:{sub_strategy_name}"
                    stock_code = trade_day_data['stock_code']
                    order_type = trade_day_data['order_type']
                    order_price = trade_day_data['order_price']
                    trade_price = trade_day_data['trade_price']
                    real_trade_price = trade_day_data['trade_price']
                    if order_type == 1:
                        trade_price = order_price
                    left_volume = trade_day_data['left_volume']
                    trade_volume = trade_day_data['trade_volume']
                    if trade_volume <= 0:
                        trade_volume = left_volume
                    if trade_volume < left_volume:
                        trade_volume = left_volume
                    
                    order_id = trade_day_data['order_id']
                    row_id =  trade_day_data['id']
                    if trade_day not in days_strategy_to_stock_volume:
                        days_strategy_to_stock_volume[trade_day] = {}
                    if strategy_name not in days_strategy_to_stock_volume[trade_day]:
                        days_strategy_to_stock_volume[trade_day][strategy_name] = []
                    days_strategy_to_stock_volume[trade_day][strategy_name].append((stock_code, left_volume, trade_price, order_id, row_id, real_trade_price, trade_volume))

        if not days_strategy_to_stock_volume:
            order_logger.info("无数据可出售")
            return

        strategy_meta_dict = {}
        with SQLiteManager(db_name) as manager:
            all_strategy_meta_infos = manager.query_data_dict("strategy_meta_info", condition_dict={'strategy_status': 1}, columns="*")
            # all_strategy_meta_infos = manager.query_data_dict("strategy_meta_info")
            if not all_strategy_meta_infos:
                order_logger.info(f"策略 没有数据， 跳过更新")
                return

            for strategy_meta_info in all_strategy_meta_infos:
                trade_at_close = strategy_meta_info['trade_at_close']
                strategy_name = strategy_meta_info['strategy_name']
                sub_strategy_name = strategy_meta_info['sub_strategy_name']
                if sub_strategy_name:
                    strategy_name = f"{strategy_name}:{sub_strategy_name}"
                budget = strategy_meta_info['budget']
                stop_loss_pct = strategy_meta_info['stop_loss_pct']
                take_profit_pct = strategy_meta_info['take_profit_pct']
                max_trade_days = strategy_meta_info['max_trade_days']
                sell_half_afternoon = strategy_meta_info['sell_half_afternoon']

                strategy_meta_dict[strategy_name] = {
                    'budget': budget,
                    'stop_loss_pct': stop_loss_pct,
                    'take_profit_pct': take_profit_pct,
                    'max_trade_days': max_trade_days,
                    'sell_half_afternoon': sell_half_afternoon,
                    'trade_at_close': trade_at_close,
                }
        ll = len(last_10_trade_days)

        sells_candidates = []
        for idx, trade_day in enumerate(last_10_trade_days):
            gap_days = ll - idx
            if trade_day in days_strategy_to_stock_volume:
                for strategy_name, strategy_stock_volumes in days_strategy_to_stock_volume[trade_day].items():
                    if strategy_name not in strategy_meta_dict:
                        order_logger.info(f"策略 {strategy_name} 没有数据， 跳过更新")
                        continue
                    strategy_meta_info = strategy_meta_dict[strategy_name]
                    budget = strategy_meta_info['budget']
                    stop_loss_pct = strategy_meta_info['stop_loss_pct']
                    take_profit_pct = strategy_meta_info['take_profit_pct']
                    max_trade_days = strategy_meta_info['max_trade_days']
                    sell_half_afternoon = strategy_meta_info['sell_half_afternoon']
                    trade_at_close = strategy_meta_info['trade_at_close']
                    if gap_days >= max_trade_days:
                        order_logger.info(f"策略 {strategy_name} 最大交易天数 {max_trade_days} 已超过 {gap_days} 天")
                        for strategy_stock_volume_info in strategy_stock_volumes:
                            stock_code = strategy_stock_volume_info[0]
                            left_volume = strategy_stock_volume_info[1]
                            trade_price = strategy_stock_volume_info[2]
                            order_id = strategy_stock_volume_info[3]
                            row_id = strategy_stock_volume_info[4]
                            real_trade_price = strategy_stock_volume_info[5]
                            trade_volume = strategy_stock_volume_info[6]
                            sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day, 'max_days', row_id, real_trade_price))
                    else:
                        if not trade_at_close:
                            continue
                        for strategy_stock_volume_info in strategy_stock_volumes:
                            stock_code = strategy_stock_volume_info[0]
                            left_volume = strategy_stock_volume_info[1]
                            trade_price = strategy_stock_volume_info[2]
                            order_id = strategy_stock_volume_info[3]
                            row_id = strategy_stock_volume_info[4]
                            real_trade_price = strategy_stock_volume_info[5]
                            trade_volume = strategy_stock_volume_info[6]

                            full_tick = xtdata.get_full_tick([stock_code])
        
                            if not full_tick or len(full_tick) == 0:
                                order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                                continue
                            elif stock_code not in full_tick:
                                order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                                continue
                            elif 'lastPrice' not in full_tick[stock_code]:
                                order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                                continue
                            elif 'lastClose' not in full_tick[stock_code]:
                                order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
                                continue
                            
                            current_price = full_tick[stock_code]['lastPrice']
                            cur_profit = current_price / trade_price - 1
                            if cur_profit >= take_profit_pct:
                                if sell_half_afternoon and left_volume > ((trade_volume // 100 + 1) // 2) * 100:
                                    sells_candidates.append((stock_code, ((trade_volume // 100 + 1) // 2) * 100, trade_price, order_id, strategy_name, trade_day,f'take_profit|{take_profit_pct}', row_id, real_trade_price))
                                else:
                                    sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day,f'take_profit|{take_profit_pct}', row_id, real_trade_price))

                            elif cur_profit < stop_loss_pct:
                                if gap_days >= 3 and '低位高强低吸' in strategy_name:
                                    continue
                                if sell_half_afternoon and left_volume > ((trade_volume // 100 + 1) // 2) * 100:
                                    sells_candidates.append((stock_code, ((trade_volume // 100 + 1) // 2) * 100, trade_price, order_id, strategy_name, trade_day,f'stop_loss|{stop_loss_pct}', row_id, real_trade_price))
                                else:
                                    sells_candidates.append((stock_code, left_volume, trade_price, order_id, strategy_name, trade_day,f'stop_loss|{stop_loss_pct}', row_id, real_trade_price))
                            else:
                                continue
        
        sells_candidates = sorted(sells_candidates, key=lambda x: x[7], reverse=True)
        if not sells_candidates:
            order_logger.info("无数据可出售")
            return
        for sells_candidate in sells_candidates:
            logger.info(f"准备出售前数据 {sells_candidate}")
        
        logger.info(f"持仓所有可出售数据 {stock_to_trade_volume}")

        codes_to_sell_infos = {}

        codes_to_sell_volume = {}

        with SQLiteManager(db_name) as manager:
            for sells_candidate in sells_candidates:
                stock_code = sells_candidate[0]
                left_volume = sells_candidate[1]
                trade_price = sells_candidate[2]
                order_id = sells_candidate[3]
                strategy_name = sells_candidate[4]
                trade_day = sells_candidate[5]
                reason = sells_candidate[6]
                row_id = sells_candidate[7]
                real_trade_price = sells_candidate[8]

                if left_volume <= 0:
                    continue

                if stock_code not in stock_to_trade_volume:
                    order_logger.info(f"股票 {stock_code} 已被出售")
                    continue
                all_volume = stock_to_trade_volume[stock_code]
                if all_volume <= 0:
                    order_logger.info(f"股票 {stock_code} 已被出售")
                    manager.update_data("trade_data", {"left_volume": 0}, {"id": row_id})
                    continue

                if left_volume > all_volume:
                    order_logger.info(f"股票 {stock_code} 准备出售 {all_volume}")
                    manager.update_data("trade_data", {"left_volume": all_volume}, {"id": row_id})
                    if stock_code in codes_to_sell_volume:
                        codes_to_sell_volume[stock_code] = codes_to_sell_volume[stock_code] + all_volume
                    else:
                        codes_to_sell_volume[stock_code] = all_volume
                    if stock_code in codes_to_sell_infos:
                        codes_to_sell_infos[stock_code].append((stock_code, left_volume, real_trade_price, row_id, strategy_name, trade_day, reason, all_volume))
                    else:
                        codes_to_sell_infos[stock_code] = [(stock_code, left_volume, real_trade_price, row_id, strategy_name, trade_day, reason, all_volume)]
                    # oid = qmt_trader.sell_quickly(stock_code, all_volume, order_remark= strategy_name,  buffer=-0.002, extra_info = sells_candidate)
                    # if oid > 0:
                    stock_to_trade_volume[stock_code] = 0
                    continue
                if left_volume <= all_volume:
                    order_logger.info(f"股票 {stock_code} 准备出售 {left_volume}")
                    if stock_code in codes_to_sell_volume:
                        codes_to_sell_volume[stock_code] = codes_to_sell_volume[stock_code] + left_volume
                    else:
                        codes_to_sell_volume[stock_code] = left_volume
                    if stock_code in codes_to_sell_infos:
                        codes_to_sell_infos[stock_code].append((stock_code, left_volume, real_trade_price, row_id, strategy_name, trade_day, reason, left_volume))
                    else:
                        codes_to_sell_infos[stock_code] = [(stock_code, left_volume, real_trade_price, row_id, strategy_name, trade_day, reason, left_volume)]

                    # oid = qmt_trader.sell_quickly(stock_code, left_volume, order_remark= strategy_name,  buffer=-0.002, extra_info = sells_candidate)
                    # if oid > 0:
                    stock_to_trade_volume[stock_code] = stock_to_trade_volume[stock_code] - left_volume
                    continue
        logger.info(f"出售后 left volume {stock_to_trade_volume}")
        
        for code, sell_volume in codes_to_sell_volume.items():
            extra_infos = codes_to_sell_infos[code]
            stock_name = offlineStockQuery.get_stock_name(code.split('.')[0])
            if not stock_name:
                stock_name = ''
            qmt_trader.sell_quickly(code, stock_name, sell_volume, order_remark= "sell",  buffer=-0.03, extra_infos = extra_infos, up_sell=False, afternoon=True)
    except Exception as e:
        print(f'exception: {e}')


def is_after_1510():
    now = datetime.datetime.now()
    target_time = now.replace(hour=15, minute=10, second=0, microsecond=0)
    return now > target_time

if __name__ == '__main__':

    is_trade, pre_trade_date = date.is_trading_day()
    if not is_trade:
        logger.info("非交易日，不更新预算。")
        exit(0)
    
    from xtquant import xtdatacenter as xtdc
    xtdc.set_token("26e6009f4de3bfb2ae4b89763f255300e96d6912")

    print('xtdc.init')
    xtdc.init() # 初始化行情模块，加载合约数据，会需要大约十几秒的时间
    print('done')

    print('xtdc.listen')
    port_list = [58611, 58612, 58613, 58614, 58615, 58616, 58617, 58618]
    selected_port = None
    listen_addr = None

    # 尝试监听端口列表中的端口
    for port in port_list:
        try:
            logger.info(f"尝试监听端口: {port}")

            listen_addr = xtdc.listen(port=port)
            selected_port = port
            logger.info(f"成功监听端口: {selected_port}, 监听地址: {listen_addr}")

            break  # 成功监听后跳出循环
        except OSError as e:
            logger.error(f"端口 {port} 监听失败: {e}")
            # 继续尝试下一个端口

    # 如果所有端口都失败
    if selected_port is None:
        logger.info("所有备选端口均监听失败，尝试扩展端口范围...")
        # 尝试58619到58630的扩展端口
        for port in range(58619, 58631):
            try:
                logger.info(f"尝试扩展端口: {port}")

                listen_addr = xtdc.listen(port=port)
                selected_port = port
                logger.info(f"成功监听扩展端口: {selected_port}, 监听地址: {listen_addr}")
                break
            except OSError as e:
                logger.error(f"扩展端口 {port} 监听失败: {e}")
        
    # 如果扩展端口也失败
    if selected_port is None:
        logger.error("所有端口均无法监听，程序退出")
        raise RuntimeError("所有端口均无法监听，程序退出")

    # listen_addr = xtdc.listen(port = 58611)
    print(f'done, listen_addr:{listen_addr}')

    qmt_trader.init_order_context(flag = True)
    qmt_trader.start_sell_listener()


    schedule_sell_stocks_everyday_at_1457()
    try:
        while True:
            print("等待1分钟...")
            if is_after_1510():
                logger.info("达到最大执行时间，退出程序")
                break
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        # 关闭调度器
        pass