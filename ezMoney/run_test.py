from http_request.build_http_request import xiao_cao_index_v2
import json

if __name__ == "__main__":
   rslt =xiao_cao_index_v2(stockCodes='001282.XSHE', date="2024-11-11", hpqbState=0, lpdxState=0)
   print(json.dumps(rslt))