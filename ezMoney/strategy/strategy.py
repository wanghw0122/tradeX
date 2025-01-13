import multiprocessing
import yaml
from logger import logger
import os

file_name = 'd:\\workspace\\TradeX\\ezMoney\\config.yml'

with open(file_name, 'r',  encoding='utf-8') as file:
    data = yaml.safe_load(file)
    if data is None:
        print("Config No data Error.")


class Strategy:
    def __init__(self, config):
        self.name = None
        self.select_func = None
        self.filters = []
        self.candidates = []
        pass
    def get_strategy(self):
        return []
    
    def get_candidates(self):
        return []
    
    def filter(self):
        pass
    
    def __call__(self, *args, **kwds):
        try:
            if self.select_func is None:
                return {}
            candidates = self.select_func()
            if candidates is None or len(candidates) == 0:
                return {}
            
        except Exception as e:
            logger.error(e)
        pass

class StrategyManager:
    def __init__(self):
        self.strategy_list = []
        self.candidate_list = []
        self.filter_list = []
        pass

    def run(self, date):
        for strategy in self.strategy_list:
            self.candidate_list.extend(strategy.get_candidates())
        for strategy in self.strategy_list:
            self.filter_list.extend(strategy.filter())
        return self.filter_list
    
    def init_strategy(self, config_path):
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
                    self.strategy_list.append(XiaoCaoDwdxA(config))
                elif name == 'xiao_cao_dwdx_d':
                    self.strategy_list.append(XiaoCaoDwdxD(config))
                else:
                    logger.error(f"strategy config name error. {name}")
        return


    def get_position_ratio(self):
        pass
    
class PositionManager:
    def __init__(self):
        pass


class XiaoCaoDwdxA(Strategy):
    def __init__(self, config):
        self.name = 'xiao_cao_dwdx_a'
        self.config = config
        self.candidate_list = []
        self.filter_list = []
        pass


class XiaoCaoDwdxD(Strategy):
    def __init__(self, config):
        self.name = 'xiao_cao_dwdx_d'
        self.config = config
        self.candidate_list = []
        self.filter_list = []
        pass


def get_current_directory():
    current_file_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_file_path)
    return current_directory

current_dir = get_current_directory()
print("当前脚本的目录路径是:", current_dir)