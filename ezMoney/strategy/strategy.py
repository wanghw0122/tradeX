import multiprocessing
import re
from numpy import inner
import yaml
from data_class.xiao_cao_index_v2 import XiaoCaoIndexResult
from data_class.category_rank_class import build_category_rank_sort_list
from logger import logger, catch
import os
from http_request import http_context
from date_utils import date
from jinja2 import Template
from data_class.xiao_cao_environment_second_line_v2 import *
from functools import wraps
from functools import lru_cache

file_name = 'D:\\workspace\\TradeX\\ezMoney\\strategy\\strategyConfig.yml'

with open(file_name, 'r',  encoding='utf-8') as file:
    data = yaml.safe_load(file)
    if data is None:
        print("Config No data Error.")


class Strategy:
    def __init__(self, config, strategy_manager):
        self.strategy_manager = strategy_manager
        self.name = config['name']
        self.type = config['type']
        self.priority = config['priority']
        self.config = config
        self.status = config['status']
        self.cached = config['cached']
        self.selectors_config = config['selectors']
        if 'maxReturnNum' in config:
            self.max_return_num = config['maxReturnNum']
        else:
            self.max_return_num = None
        if 'depends' in config:
            self.depends = [depend.strip() for depend in config['depends'].split(',')]
        else:
            self.depends = []
        self.selectors = {}
        self.selector_fucs = []
        self.filters = {}
        self.running_context = {}
        self.log_filters = set()
        self._build_selectors()
        

    def _build_selectors(self):
        self.selectors_config = sorted(self.selectors_config, key=lambda x: x['step'])
        for selector_config in self.selectors_config:
            selector_name = selector_config['name']
            if 'lruCached' in selector_config:
                lru_cached = selector_config['lruCached']
            else:
                lru_cached = False
            self.selectors[selector_name] = selector_config
            selector_fuc = self.strategy_manager.get_selector(selector_name)
            if selector_fuc is None:
                raise Exception(f"selector {selector_name} not found.")
            if lru_cached:
                selector_fuc = lru_cache(maxsize=32)(selector_fuc)
                selector_fuc.__name__ = selector_name
            self.selector_fucs.append(selector_fuc)
            if 'filters' in selector_config and selector_config['filters'] is not None:
                selector_config['filters'] = sorted(selector_config['filters'], key=lambda x: x['index'])
                for filter_config in selector_config['filters']:
                    filter_name = filter_config['name']
                    filter_fuc = self.strategy_manager.get_filter(filter_name)
                    if filter_fuc is None:
                        raise Exception(f"filter {filter_name} not found.")
                    if 'params' in filter_config and filter_config['params'] is not None and len(filter_config['params']) > 0:
                        filter_fuc = filter_fuc(**filter_config['params'])
                    filter_fuc.__name__ = filter_name
                    if selector_name in self.filters:
                        self.filters[selector_name].append(filter_fuc)
                        if 'logged' in filter_config and filter_config['logged']:
                            self.log_filters.add(filter_fuc)
                    else:
                        self.filters[selector_name] = [filter_fuc]
            else:
                self.filters[selector_name] = []

    def get_selector(self, name):
        return self.selectors_config[name]
    
    def run(self, current_date = date.get_current_date(), **kwargs):
        if self.status == 0:
            logger.info(f"策略 {self.name} 状态有误 跳过执行.")
            return
        is_trade_date, _ = date.is_trading_day(current_date)
        if is_trade_date == False:
            logger.error(f"{current_date} 非交易日期 跳过执行.")
            return None
        self.running_context['system_time'] = current_date
        if kwargs is not None and len(kwargs) > 0:
            self.running_context.update(kwargs)
        if 'sub_task' in self.running_context and self.running_context['sub_task']:
            logger.info(f"策略-{self.name} 子任务-{self.running_context['sub_task']} 开始运行. 运行在日期 : {current_date}")
        else:
            logger.info(f"策略-{self.name} 开始运行. 运行在日期 : {current_date}")
        def run_result():
            try:
                if self.selector_fucs is None or len(self.selector_fucs) == 0:
                    return None
                selector_fucs = self.selector_fucs
                for selector_fuc in selector_fucs:
                    selector_name = selector_fuc.__name__
                    params = self.selectors[selector_name]['params']
                    logged = self.selectors[selector_name]['logged']
                    cached = False
                    if 'cached' in self.selectors[selector_name] and self.selectors[selector_name]['cached']:
                        cached = True
                    if params is not None:
                        template = Template(yaml.dump(params))
                        params = yaml.safe_load(template.render(self.running_context))
                        # logger.info(f"{selector_name} render result params is {params}")
                        selector_rslt = selector_fuc(**params)
                    else:
                        selector_rslt = selector_fuc()
                    if selector_rslt is None or len(selector_rslt) == 0:
                        logger.info(f"选择器 {selector_name} 结果为空")
                        if cached and selector_name in self.running_context:
                            self.running_context.pop(selector_name)
                        return None
                    else:
                        if type(selector_rslt) == list or type(selector_rslt) == tuple or type(selector_rslt) == set or type(selector_rslt) == dict:
                            logger.info (f"选择器 {selector_name} 查询到的结果数目: {len(selector_rslt)}")
                        # logger.info(f"{selector_name} selector result success.")
                        if logged:
                            logger.info(f"选择器 {selector_name} 结果是 {selector_rslt}")
                    if selector_name in self.filters:
                        for filter_fuc in self.filters[selector_name]:
                            selector_rslt = filter_fuc(selector_rslt, self.running_context)
                            if selector_rslt is None or len(selector_rslt) == 0:
                                logger.info(f"过滤器 {selector_name}.{filter_fuc.__name__} 结果为空")
                                return None
                            else:
                                # logger.info(f"{selector_name}.{filter_fuc.__name__} filter result success.")
                                if filter_fuc in self.log_filters:
                                    logger.info(f"过滤器 {selector_name}.{filter_fuc.__name__} 结果是 {selector_rslt}")
                    if not cached:
                        logger.info(f"选择器 {selector_name} 跳过缓存")
                        continue
                    else:
                        self.running_context[selector_name] = selector_rslt
                return selector_rslt
            except Exception as e:
                
                logger.error(f"run_result error. {e}", exc_info=True)

        rslt = run_result()
        self.running_context.clear()
        return rslt
            

class StrategyManager:
    def __init__(self):
        self.selectors_funcs= {}
        self.filters_funcs = {}
        self.strategy_list = []
        self.strategy_dict = {}

    def register_selector(self, name, func):
        self.selectors_funcs[name] = func
    
    def register_filter(self, name, func):
        self.filters_funcs[name] = func

    def get_selector(self, name):
        return self.selectors_funcs[name]
    
    def get_filter(self, name):
        return self.filters_funcs[name]
    
    def init_strategys(self, config_path):
        with open(config_path, 'r',  encoding='utf-8') as file:
            data = yaml.safe_load(file)
            if data is None:
                logger.error("strategy config data Error.")
                return
            if 'Strategies' not in data:
                logger.error("strategy config no Strategies.")
                return
            data = data['Strategies']
            for config in data:
                if 'name' not in config:
                    logger.info("strategy config no Name.")
                    continue
                name = config['name']
                if name == '':
                    logger.error("strategy config no Name.")
                    continue
                elif name == 'xiao_cao_dwdx_a' or name == 'xiao_cao_dwndx' or name == 'xiao_cao_dwyxdx':
                    xcd = XiaoCaoDwdxA(config, self)
                    self.strategy_list.append(xcd)
                    self.strategy_dict[name] = xcd
                elif name == 'xiao_cao_dwdx_d':
                    # xcd = XiaoCaoDwdxD(config, self)
                    # self.strategy_list.append(xcd)
                    # self.strategy_dict[name] = xcd
                    pass
                elif name == '低吸':
                    dx = DxStrategy(config, self)
                    self.strategy_list.append(dx)
                    self.strategy_dict[name] = dx
                elif name == '追涨':
                    qb = QbStrategy(config, self)
                    self.strategy_list.append(qb)
                    self.strategy_dict[name] = qb
                elif name == '接力':
                    jw = JwStrategy(config, self)
                    self.strategy_list.append(jw)
                    self.strategy_dict[name] = jw
                elif name == 'xiao_cao_1j2db' or name == 'xiao_cao_1j2db_1':
                    db = DbOne(config, self)
                    self.strategy_list.append(db)
                    self.strategy_dict[name] = db
                else:
                    stg = Strategy(config, self)
                    self.strategy_list.append(stg)
                    self.strategy_dict[name] = stg
            if len(self.strategy_list) > 1:
                self.strategy_list = sorted(self.strategy_list, key=lambda x: x.priority)

    def run_strategys(self, strategy_names, current_date = date.get_current_date(), sub_task = None, params = {}):
        kwargs = {}
        if sub_task is not None:
            kwargs['sub_task'] = sub_task
        if params is not None and len(params) > 0:
            kwargs.update(params)
        return_result = {}
        if strategy_names is None or len(strategy_names) == 0:
            return return_result
        run_strategys = []
        for strategy_name in strategy_names:
            logger.info(f'start run strategy_name: {strategy_name}')
            strategy = self.get_strategy(strategy_name)
            if strategy is None:
                logger.error(f"strategy {strategy_name} not found. or status is 0.")
                continue
            run_strategys.append(strategy)
            if strategy.depends is not None and len(strategy.depends) > 0:
                for depend in strategy.depends:
                    depend_strategy = self.get_strategy(depend)
                    if depend_strategy is None:
                        logger.error(f"strategy {strategy_name}'s depend-{depend} not found. or status is 0.")
                        continue
                    if depend_strategy in run_strategys:
                        continue
                    run_strategys.append(depend_strategy)
        run_strategys = sorted(run_strategys, key=lambda x: x.priority)
        for strategy in run_strategys:
            rslt = strategy.run(current_date, **kwargs)
            return_result[strategy.name] = rslt
        return return_result
    

    def get_strategy(self, name):
        if name not in self.strategy_dict:
            return None
        if self.strategy_dict[name].status == 0:
            return None
        return self.strategy_dict[name]

    def run_all_strategys(self, strategies_dict = {}, current_date = date.get_current_date()):
        logger.info(f"strategies_dict: {strategies_dict}")
        return_rslt = {}
        if strategies_dict is None or len(strategies_dict) == 0:
            return {}
        all_valid_strategy_names = self.get_all_strategy_names()
        for strategy_name, sub_task_dict in strategies_dict.items():
            if strategy_name not in all_valid_strategy_names:
                logger.info(f"策略 {strategy_name} 无效，取消执行.")
                continue
            if 'sub_strategies' in sub_task_dict and sub_task_dict['sub_strategies']:
                sub_strategies = sub_task_dict['sub_strategies']
                for sub_task, params in sub_strategies.items():
                    rslt = self.run_strategys([strategy_name], current_date, sub_task, params)
                    return_rslt[strategy_name + '-' + sub_task] = rslt
            
            else:
                rslt = self.run_strategys([strategy_name], current_date, params=sub_task_dict)
                return_rslt[strategy_name] = rslt
        return return_rslt


    def get_all_strategy_names(self):
        return [strategy.name for strategy in self.strategy_list if strategy.status > 0]


class XiaoCaoDwdxA(Strategy):
    def __init__(self, config, strategy_manager):
        super().__init__(config, strategy_manager)
        pass

    def run(self, current_date=date.get_current_date(), **kwargs):
        s_result = super().run(current_date, **kwargs)
        if s_result is None or len(s_result) == 0:
            return None
        s_result.sort(key=lambda x: x.cjs, reverse=True)
        if self.max_return_num:
            s_result = s_result[:self.max_return_num]
            if s_result is None or len(s_result) == 0:
                return None
        if 'returnFullInfo' not in kwargs or not kwargs['returnFullInfo']:
            rs = [x.code for x in s_result]
        else:
            rs = s_result
        if 'returnNum' in kwargs and kwargs['returnNum']:
            return rs[:kwargs['returnNum']]
        return rs

class XiaoCaoDwdxD(Strategy):
    def __init__(self, config, strategy_manager):
        super().__init__(config, strategy_manager)
        pass

class DxStrategy(Strategy):
    def __init__(self, config, strategy_manager):
        super().__init__(config, strategy_manager)
        pass

    def run(self, current_date=date.get_current_date(), **kwargs):
        s_result = super().run(current_date, **kwargs)
        if s_result is None or len(s_result) == 0:
            return None
        s_result.sort(key=lambda x: x.cjs, reverse=True)
        if self.max_return_num:
            s_result = s_result[:self.max_return_num]
            if s_result is None or len(s_result) == 0:
                return None
        if 'returnFullInfo' not in kwargs or not kwargs['returnFullInfo']:
            rs = [x.code for x in s_result]
        else:
            rs = s_result
        if 'returnNum' in kwargs and kwargs['returnNum'] >= 0:
            return rs[:kwargs['returnNum']]
        return rs

class DbOne(Strategy):
    def __init__(self, config, strategy_manager):
        super().__init__(config, strategy_manager)
        pass

    def run(self, current_date=date.get_current_date(), **kwargs):
        s_result = super().run(current_date, **kwargs)
        if s_result is None or len(s_result) == 0:
            return None
        s_result.sort(key=lambda x: x.jsjl, reverse=True)
        if self.max_return_num:
            s_result = s_result[:self.max_return_num]
            if s_result is None or len(s_result) == 0:
                return None
        rs = []
        rs.append(s_result[0])
        s_result.sort(key=lambda x: x.xcjw, reverse=True)
        x = s_result[0]
        if x.code != rs[0].code:
            rs.append(x)
        if 'returnFullInfo' not in kwargs or not kwargs['returnFullInfo']:
            rs = [x.code for x in rs]
        if 'returnNum' in kwargs and kwargs['returnNum']:
            return rs[:kwargs['returnNum']]
        return rs

class JwStrategy(Strategy):
    def __init__(self, config, strategy_manager):
        super().__init__(config, strategy_manager)
        pass

    def run(self, current_date=date.get_current_date(), **kwargs):
        s_result = super().run(current_date, **kwargs)
        if s_result is None or len(s_result) == 0:
            return None
        s_result.sort(key=lambda x: x.xcjw, reverse=True)
        if self.max_return_num:
            s_result = s_result[:self.max_return_num]
            if s_result is None or len(s_result) == 0:
                return None
        if 'returnFullInfo' not in kwargs or not kwargs['returnFullInfo']:
            rs = [x.code for x in s_result]
        else:
            rs = s_result
        if 'returnNum' in kwargs and kwargs['returnNum']:
            return rs[:kwargs['returnNum']]
        return rs

class QbStrategy(Strategy):
    def __init__(self, config, strategy_manager):
        super().__init__(config, strategy_manager)
        pass

    def run(self, current_date=date.get_current_date(), **kwargs):
        s_result = super().run(current_date, **kwargs)
        if s_result is None or len(s_result) == 0:
            return None
        s_result.sort(key=lambda x: x.jssb, reverse=True)
        if self.max_return_num:
            s_result = s_result[:self.max_return_num]
            if s_result is None or len(s_result) == 0:
                return None
        if 'returnFullInfo' not in kwargs or not kwargs['returnFullInfo']:
            rs = [x.code for x in s_result]
        else:
            rs = s_result
        if 'returnNum' in kwargs and kwargs['returnNum']:
            return rs[:kwargs['returnNum']]
        return rs


def count_filtered_items(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        before_count = len(args[0]) if args and args[0] else 0
        result = func(*args, **kwargs)
        if callable(result):
            return count_filtered_items(result)
        after_count = len(result) if result else 0
        function_name = func.__name__
        filter_count = before_count - after_count
        logger.info(f"过滤器 {function_name} 过滤的数量为 : {filter_count}")
        return result
    # wrapper.__name__ = func.__name__
    return wrapper



@count_filtered_items
@catch
def item_code_filter(*args, **kwargs):
    arr = args[0]
    if not arr:
        return None
    return [item.code for item in arr]

@count_filtered_items
@catch
def keys_10cm_filter(*args, **kwargs):
    arr = args[0]
    filtered_arr = []
    for code in arr:
        if code.startswith('60') or code.startswith('00'):
            filtered_arr.append(code)
    return filtered_arr

@count_filtered_items
@catch
def limiter_filter(limit):
    def inner_filter(*args, **kwargs):
        arr = args[0]
        return arr[:limit]
    inner_filter.__name__ = "limiter_filter"
    return inner_filter

@count_filtered_items
@catch
def st_filter(*args, **kwargs):
    arr = args[0]
    return [item for item in arr if not item.isPreSt]


@count_filtered_items
@catch
def n_filter(*args, **kwargs):
    arr = args[0]
    return [item for item in arr if item.firstLimitUpDays > 0]

@count_filtered_items
@catch
def yx_filter(*args, **kwargs):
    arr = args[0]
    return [item for item in arr if item.isGestationLine]

@count_filtered_items
@catch
def first_bottom_filter(*args, **kwargs):
    rslt = []
    arr = args[0]
    cxt = args[1]
    current_date = cxt['system_time']
    for item in arr:
        if item.openPctChangeRate >= -9.7:
            rslt.append(item)
            continue
        kline_fuc = http_context['date_kline']
        klines = kline_fuc(code=item.code, count=300, freq="D", adj="bfq")
        logger.info(f"获取{item.code}的300天K线数据.")
        if klines == None:
            rslt.append(item)
            continue
        else:
            logger.info(f"获取{item.code}的300天K线数据成功.")
            is_trade, previous_date = date.is_trading_day(current_date)
            logger.info(f"获取{current_date}的前一个交易日 为{previous_date}.")
            if '-' in previous_date:
                previous_date = previous_date.replace('-', '')
            if not is_trade:
                raise Exception(f"Not trading day. {current_date}")
            for kline in klines:
                if kline['tradeDate'] == previous_date:
                    logger.info(f"获取{previous_date}pctChangeRate {kline['pctChangeRate']} .")
                    if kline['pctChangeRate'] and kline['pctChangeRate'] < -9.7:
                        rslt.append(item)
                    break
    return rslt


@count_filtered_items
@catch
def jw_filter(xcjwScore = 200):
    def inner_filter(*args, **kwargs):
        arr = args[0]
        return [item for item in arr if item.xcjw and item.xcjw >= xcjwScore]
    inner_filter.__name__ = "jw_filter"
    return inner_filter

@count_filtered_items
@catch
def dx_filter(xcdxScore = 100):
    def inner_filter(*args, **kwargs):
        arr = args[0]
        return [item for item in arr if item.cjs and item.cjs >= xcdxScore]
    inner_filter.__name__ = "dx_filter"
    return inner_filter




@count_filtered_items
@catch
def openPctChangeRate_filter(openPctChangeRate = 0):
    def inner_filter(*args, **kwargs):
        arr = args[0]
        return [item for item in arr if item.openPctChangeRate != None and item.openPctChangeRate >= openPctChangeRate]
    inner_filter.__name__ = "openPctChangeRate_filter"
    return inner_filter

@count_filtered_items
@catch
def qb_filter(xcqbScore = 100):
    def inner_filter(*args, **kwargs):
        arr = args[0]
        return [item for item in arr if item.jssb and item.jssb >= xcqbScore]
    inner_filter.__name__ = "qb_filter"
    return inner_filter


@count_filtered_items
@catch
def jl_filter(xcjlScore = 1):
    def inner_filter(*args, **kwargs):
        arr = args[0]
        return [item for item in arr if item.jsjl and item.jsjl > xcjlScore]
    inner_filter.__name__ = "jl_filter"
    return inner_filter

@count_filtered_items
@catch
def stock_type_filter(**args):
    def inner_filter(*iargs, **kwargs):
        arr = iargs[0]
        if not arr or  len(args) == 0:
            return arr
        rtn = []
        for item in arr:
            if 'isGestationLine' in args and item.isGestationLine != args['isGestationLine']:
                continue
            if 'isBrokenPlate' in args and item.isBrokenPlate != args['isBrokenPlate']:
                continue
            if 'isSmallHighOpen' in args and item.isSmallHighOpen != args['isSmallHighOpen']:
                continue
            if 'isWeak' in args and item.isWeak!= args['isWeak']:
                continue
            if 'isLongShadow' in args and item.isLongShadow!= args['isLongShadow']:
                continue
            if 'isUpBroken' in args and item.isUpBroken!= args['isUpBroken']:
                continue
            if 'isFirstUpBroken' in args and item.isFirstUpBroken!= args['isFirstUpBroken']:
                continue
            if 'isDownBroken' in args and item.isDownBroken!= args['isDownBroken']:
                continue
            if 'isFirstDownBroken' in args and item.isFirstDownBroken!= args['isFirstDownBroken']:
                continue
            if 'isHalf' in args and item.isHalf!= args['isHalf']:
                continue
            if 'isBottom' in args and item.isBottom!= args['isBottom']:
                continue
            if 'isPreSt' in args and item.isPreSt!= args['isPreSt']:
                continue
            if 'isMedium' in args and item.isMedium!= args['isMedium']:
                continue
            if 'isHigh' in args and item.isHigh!= args['isHigh']:
                continue
            if 'isMeso' in args and item.isMeso!= args['isMeso']:
                continue
            if 'isLow' in args and item.isLow!= args['isLow']:
                continue
            if 'isFall' in args and item.isFall!= args['isFall']:
                continue
            if 'isPlummet' in args and item.isPlummet!= args['isPlummet']:
                continue
            if 'isHighest' in args and item.isHighest!= args['isHighest']:
                continue
            if 'ylimitupdays' in args and item.ylimitupdays!= args['ylimitupdays']:
                continue
            rtn.append(item)
        return rtn
    inner_filter.__name__ = "stock_type_filter"
    return inner_filter

def get_current_config(config_file = 'strategyConfig.yml'):
    import os
    current_file_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_file_path)
    return os.path.join(current_directory, config_file)


@count_filtered_items
@catch
def change_item_filter(*args, **kwargs):
    arr = args[0]
    if arr == None:
        return []
    
    if type(arr) == list:
        return [XiaoCaoIndexResult(**item) for item in arr]
    elif type(arr) == dict:
        return [XiaoCaoIndexResult(**item) for _, item in arr.items()]
    else:
        return []


def get_code_by_block_rank(tradeDate, ranks, blockCodeList = "", industryBlockCodeList = "",categoryCodeList = "",exponentCodeList = ""):
    codes =  build_http_request.get_code_by_xiao_cao_block_rank(blockCodeList, industryBlockCodeList,categoryCodeList,exponentCodeList,tradeDate)
    if not ranks or len(ranks) == 0:
        logger.error("get_code_by_block_rank, sort_v2 ranks is None.")
        return codes
    ranklist = ranks.split(",")
    if codes == None or len(codes) == 0:
        return None
    if len(codes) == 1:
        return codes
    rank_codes = []
    for code in ranklist:
        if not codes or len(codes) == 0:
            break
        if code in codes:
            rank_codes.append(code)
            codes.remove(code)
    return rank_codes


sm = StrategyManager()
sm.register_selector("check_user_alive", http_context['check_user_alive'])
sm.register_selector("system_time", http_context['system_time'])
sm.register_selector("sort_v2", http_context['sort_v2'])
sm.register_selector("xiao_cao_index_v2", http_context['xiao_cao_index_v2'])
sm.register_selector("build_xiaocao_environment_second_line_v2_dict_simple", build_xiaocao_environment_second_line_v2_dict_simple)
sm.register_selector("build_xiaocao_mod_dict_all", build_xiaocao_mod_dict_all)
sm.register_selector("get_code_by_block_rank", get_code_by_block_rank)
sm.register_selector("build_category_rank_sort_list", build_category_rank_sort_list)

sm.register_filter("keys_10cm_filter", keys_10cm_filter)
sm.register_filter("jw_filter", jw_filter)
sm.register_filter("jl_filter", jl_filter)
sm.register_filter("st_filter", st_filter)
sm.register_filter("dx_filter", dx_filter)
sm.register_filter("qb_filter", qb_filter)
sm.register_filter("n_filter", n_filter)
sm.register_filter("yx_filter", yx_filter)
sm.register_filter("first_bottom_filter", first_bottom_filter)
sm.register_filter("stock_type_filter", stock_type_filter)
sm.register_filter("change_item_filter", change_item_filter)
sm.register_filter("item_code_filter", item_code_filter)
sm.register_filter("limiter_filter", limiter_filter)
sm.register_filter("openPctChangeRate_filter", openPctChangeRate_filter)
sm.init_strategys(get_current_config())



