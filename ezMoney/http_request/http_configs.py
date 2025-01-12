import requests
import yaml


file_name = 'd:\\workspace\\TradeX\\ezMoney\\config.yml'

with open(file_name, 'r',  encoding='utf-8') as file:
    data = yaml.safe_load(file)
    if data is None:
        print("Config No data Error.")


requests_urls  = {}

def build_data(data) :
    replaced = {
        '{{Cookie}}': data["Cookie"],
        '{{head}}': data["head"]
    }
    urls = data['Steps']['urls']
    for url in urls:
        for k, v in url.items():
            if v in replaced:
                url[k] = replaced[v]

def build_requests_urls(request_urls, data):
    urls = data['Steps']['urls']
    for url in urls:
        requests_urls[url['name']] = url

build_data(data)
build_requests_urls(requests_urls, data)

if __name__ == '__main__':
    pass
