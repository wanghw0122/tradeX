import yaml
from jinja2 import Template
from datetime import datetime


# 读取 YAML 文件
with open('D:\\workspace\\TradeX\\ezMoney\\strategy\\testConfig.yml', 'r', encoding='utf-8') as file:
    global config
    config = yaml.safe_load(file)
    # print(config)

# 获取 sort_v2 和 system_time 的值
sort_v2 = ['stock1', 'stock2', 'stock3']
system_time = '2023-10-10'

m = {
    'sort_v2': sort_v2,
    'system_time': system_time,
    'stock1': '600000'
}

# print(yaml.dump(config))

# 遍历 Strategies 列表
for strategy in config['Strategies']:
    if strategy['name'] == 'xiao_cao_dwdx_a':
        # 遍历 selectors 列表
        for selector in strategy['selectors']:
            if selector['name'] == 'xiao_cao_index_v2':
                print(yaml.dump(selector['params']))
                # 使用 Jinja2 模板进行参数替换
                template = Template(yaml.dump(selector['params']))
                selector['params'] = yaml.safe_load(template.render(m))
                print(yaml.dump(selector['params']))

# 打印替换后的 YAML 内容
print(type(config))

from decimal import Decimal, ROUND_HALF_UP
 
num = Decimal('3.195')
rounded_num = num.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

print(rounded_num)