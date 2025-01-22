import multiprocessing
import re
import yaml
from data_class.xiao_cao_index_v2 import XiaoCaoIndexResult
from logger import logger, catch
import os
from http_request import http_context
from date_utils import date
from jinja2 import Template
from data_class.xiao_cao_environment_second_line_v2 import *

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
        self.config = config
        self.status = config['status']
        self.cached = config['cached']
        self.selectors_config = config['selectors']
        self.selectors = {}
        self.selector_fucs = []
        self.filters = {}
        self._build_selectors()
        self.running_context = {}

    def _build_selectors(self):
        self.selectors_config = sorted(self.selectors_config, key=lambda x: x['step'])
        for selector_config in self.selectors_config:
            selector_name = selector_config['name']
            self.selectors[selector_name] = selector_config
            selector_fuc = self.strategy_manager.get_selector(selector_name)
            if selector_fuc is None:
                raise Exception(f"selector {selector_name} not found.")
            self.selector_fucs.append(selector_fuc)
            if 'filters' in selector_config and selector_config['filters'] is not None:
                selector_config['filters'] = sorted(selector_config['filters'], key=lambda x: x['index'])
                for filter_config in selector_config['filters']:
                    filter_name = filter_config['name']
                    filter_fuc = self.strategy_manager.get_filter(filter_name)
                    if filter_fuc is None:
                        raise Exception(f"filter {filter_name} not found.")
                    if 'params' in filter_config and filter_config['params'] is not None:
                        filter_fuc = filter_fuc(**filter_config['params'])
                    if selector_name in self.filters:
                        self.filters[selector_name].append(filter_fuc)
                    else:
                        self.filters[selector_name] = [filter_fuc]
            else:
                self.filters[selector_name] = []

    def get_selector(self, name):
        return self.selectors_config[name]
    
    def run(self, current_date = date.get_current_date()):
        if self.status == 0:
            logger.info(f"{self.name} is not set running.")
            return
        is_trade_date = date.is_trade_date(current_date)
        if is_trade_date == False:
            logger.error(f"{current_date} is not trade date.")
            return None
        self.running_context['system_time'] = current_date
        logger.info(f"{self.name} is running. date : {current_date}")
        def run_result():
            try:
                if self.selector_fucs is None or len(self.selector_fucs) == 0:
                    return []
                selector_fucs = self.selector_fucs
                for selector_fuc in selector_fucs:
                    selector_name = selector_fuc.__name__
                    params = self.selectors[selector_name]['params']
                    if params is not None:
                        template = Template(yaml.dump(params))
                        params = yaml.safe_load(template.render(self.running_context))
                        logger.info(f"{selector_name} params is {params}")
                        selector_rslt = selector_fuc(**params)
                    else:
                        selector_rslt = selector_fuc()
                    if selector_rslt is None or len(selector_rslt) == 0:
                            logger.info(f"{selector_name} selector result is None.")
                            return None
                    else:
                        logger.info(f"{selector_name} selector result is {selector_rslt}")
                    if selector_name in self.filters:
                        for filter_fuc in self.filters[selector_name]:
                            selector_rslt = filter_fuc(selector_rslt)
                            if selector_rslt is None or len(selector_rslt) == 0:
                                logger.info(f"{selector_name}.{filter_fuc.__name__} filter result is None.")
                                return None
                            else:
                                logger.info(f"{selector_name}.{filter_fuc.__name__} filter result is {selector_rslt}")
                    if 'cached' in self.selectors[selector_name] and not self.selectors[selector_name]['cached']:
                        logger.info(f"{selector_name} selector result is not cached.")
                        continue
                    else:
                        self.running_context[selector_name] = selector_rslt
                return selector_rslt
            except Exception as e:
                logger.error(e)

        return run_result()
            

class StrategyManager:
    def __init__(self):
        self.selectors_funcs= {}
        self.filters_funcs = {}
        self._init_selectors()
        self._init_filters()
        self.strategy_list = []
    

    def _init_selectors(self):
        self.selectors_funcs['check_user_alive'] = http_context['check_user_alive']
        self.selectors_funcs['system_time'] = http_context['system_time']
        self.selectors_funcs['sort_v2'] = http_context['sort_v2']
        self.selectors_funcs['xiao_cao_index_v2'] = http_context['xiao_cao_index_v2']
        self.selectors_funcs['build_xiaocao_environment_second_line_v2_dict_simple'] = build_xiaocao_environment_second_line_v2_dict_simple

    def _init_filters(self):
        self.filters_funcs['keys_10cm_filter'] = keys_10cm_filter
        self.filters_funcs['limiter_filter'] = limiter_filter
        self.filters_funcs['st_filter'] = st_filter
        self.filters_funcs['first_bottom_filter'] = first_bottom_filter
        self.filters_funcs['jw_filter'] = jw_filter
        self.filters_funcs['change_item_filter'] = change_item_filter
        self.filters_funcs['stock_type_filter'] = stock_type_filter

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
                    print("strategy config no Name.")
                    continue
                name = config['name']
                if name == '':
                    logger.error("strategy config no Name.")
                    continue
                elif name == 'xiao_cao_dwdx_a':
                    self.strategy_list.append(XiaoCaoDwdxA(config, self))
                elif name == 'xiao_cao_dwdx_d':
                    # self.strategy_list.append(XiaoCaoDwdxD(config, self))
                    pass
                elif name == 'xiao_cao_env':
                    self.strategy_list.append(Strategy(config, self))
                else:
                    logger.error(f"strategy config name error. {name}")
    def run_strategys(self, current_date = date.get_current_date()):
        return_result = {}
        for strategy in self.strategy_list:
            rslt = strategy.run(current_date)
            return_result[strategy.name] = rslt
        return return_result


class XiaoCaoDwdxA(Strategy):
    def __init__(self, config, strategy_manager):
        super().__init__(config, strategy_manager)
        pass

    def run(self, current_date=date.get_current_date()):
        s_result = super().run(current_date)
        if s_result is None or len(s_result) == 0:
            return None
        else:
            return [x.code for x in s_result]


class XiaoCaoDwdxD(Strategy):
    def __init__(self, config, strategy_manager):
        super().__init__(config, strategy_manager)
        pass

@catch
def keys_10cm_filter(arr):
    filtered_arr = []
    for code in arr:
        if code.startswith('60') or code.startswith('00'):
            filtered_arr.append(code)
    return filtered_arr

@catch
def limiter_filter(limit):
    def inner_filter(arr):
        return arr[:limit]
    return inner_filter


@catch
def st_filter(arr):
    return [item for item in arr if not item.isPreSt]

@catch
def first_bottom_filter(arr):
    rslt = []
    for item in arr:
        if item.openPctChangeRate and item.openPctChangeRate >= -9.7:
            rslt.append(item)
            continue
        kline_fuc = http_context['date_kline']
        klines = kline_fuc(code=item.code, count=300, freq="D", adj="bfq")
        if klines == None:
            rslt.append(item)
            continue
        else:
            is_trade, previous_date = date.is_trading_day()
            if not is_trade:
                raise Exception("Not trading day.")
            for kline in klines:
                if kline['tradeDate'] == previous_date:
                    if kline['pctChange'] and kline['pctChange'] < -9.7:
                        rslt.append(item)
                    break
    return rslt

@catch
def jw_filter(xcjwScore = 200):
    def inner_filter(arr):
        return [item for item in arr if item.xcjw and item.xcjw >= xcjwScore]
    return inner_filter


def stock_type_filter(**args):
    def inner_filter(arr):
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
            rtn.append(item)
        return rtn
    return inner_filter

def get_current_config(config_file = 'strategyConfig.yml'):
    import os
    current_file_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_file_path)
    return os.path.join(current_directory, config_file)

def change_item_filter(arr):
    if arr == None:
        return []
    
    if type(arr) == list:
        return [XiaoCaoIndexResult(**item) for item in arr]
    elif type(arr) == dict:
        return [XiaoCaoIndexResult(**item) for _, item in arr.items()]
    else:
        return []

sm = StrategyManager()
sm.init_strategys(get_current_config())