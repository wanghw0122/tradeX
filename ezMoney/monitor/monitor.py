from common import constants
from sqlite_processor.mysqlite import SQLiteManager
import threading
import queue
from date_utils import date
import datetime
from logger import strategy_logger as logger
from monitor.kline_strategy import SimplifiedKLineStrategy
import time as tm

def calculate_seconds_difference(specified_time):
    current_time = datetime.datetime.now().timestamp()
    time_difference =  current_time - (specified_time / 1000)
    return time_difference

monitor_table = 'monitor_data'
monitor_config_table = "strategy_monitor_config"


### 与回测不一致在于：
### 1. 高开情况下，均线下，均线在开盘上方，容忍在开盘价卖出，是否容忍最大观察步长

strategy_to_params_configs = {
        '接力-一进二弱转强:倒接力4': {
            "per_step_tick_gap": 24,
            "cold_start_steps": 49,
            "max_abserve_tick_steps": 437,
            "max_abserce_avg_price_down_steps": 3,
            "stop_profit_open_hc_pct": -0.13686809451794058,
            "dynamic_hc_stop_profit_thres": 7.905323301277404,
            "last_close_price_hc_pct": -0.01378889765900443,
            "last_day_sell_thres": 0.9865163211147541,
            "last_day_sell_huiche": 0.0036576065059504537,
            "fd_mount": 94608769,
            "fd_vol_pct": 0.4754080291012261,
            "fd_ju_ticks": 1,
            "max_zb_times": 1,
            "stagnation_kline_ticks": 21,
            "decline_kline_ticks": 29,
            "yang_yin_threshold": 0.006176144608813387,
            "stagnation_n": 25,
            "stagnation_volume_ratio_threshold": 77.7474566373611,
            "stagnation_ratio_threshold": 163,
            "decline_volume_ratio_threshold": 91.82170264800575,
            "max_rebounds": 12,
            "decline_ratio_threshold": 989,
            "flxd_ticks": 358,
            "flzz_ticks": 1347,
            "use_simiple_kline_strategy_flxd": False,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": 0.01663289495872894,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.04148311115631363,
            "open_price_max_hc": -0.026297748471545673,
            "loss_per_step_tick_gap": 5,
            "loss_cold_start_steps": 5,
            "loss_max_abserve_tick_steps": 86,
            "loss_max_abserce_avg_price_down_steps": 9,
            "loss_dynamic_hc_stop_profit_thres": 0.8025313113307362,
            "loss_last_close_price_hc_pct": -0.03260582448719203,
            "loss_last_open_price_hc_pct": -0.04094958032808486,
            "loss_open_price_max_hc": -0.05682764936424609,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.0,
            "day_zs_line": -0.01995892241356487,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 3,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
        '接力-一进二弱转强:倒接力41': {
            "per_step_tick_gap": 14,
            "cold_start_steps": 22,
            "max_abserve_tick_steps": 487,
            "max_abserce_avg_price_down_steps": 2,
            "stop_profit_open_hc_pct": -0.14630701919345082,
            "dynamic_hc_stop_profit_thres": 7.345315336128041,
            "last_close_price_hc_pct": 0.008799263737105115,
            "last_day_sell_thres": 0.01,
            "last_day_sell_huiche": 0.008504364805503928,
            "fd_mount": 149997849,
            "fd_vol_pct": 0.4303184525735707,
            "fd_ju_ticks": 1,
            "max_zb_times": 1,
            "stagnation_kline_ticks": 19,
            "decline_kline_ticks": 6,
            "yang_yin_threshold": 0.0035769409020040004,
            "stagnation_n": 28,
            "stagnation_volume_ratio_threshold": 64.65718515930423,
            "stagnation_ratio_threshold": 589,
            "decline_volume_ratio_threshold": 10.517979950856365,
            "max_rebounds": 1,
            "decline_ratio_threshold": 424,
            "flxd_ticks": 0,
            "flzz_ticks": 1089,
            "use_simiple_kline_strategy_flxd": False,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": 0.032049576277843626,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.05182383071196173,
            "open_price_max_hc": -0.007890569537497151,
            "loss_per_step_tick_gap": 5,
            "loss_cold_start_steps": 28,
            "loss_max_abserve_tick_steps": 145,
            "loss_max_abserce_avg_price_down_steps": 1,
            "loss_dynamic_hc_stop_profit_thres": 3.096720217898729,
            "loss_last_close_price_hc_pct": -0.031885425487096185,
            "loss_last_open_price_hc_pct": -0.010842204918918068,
            "loss_open_price_max_hc": -0.06352933084142115,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": True,
            "day_zy_line": 2.786201483567871e-05,
            "day_zs_line": -0.019670266330581256,
            "sell_afternoon": False,
            "sell_half_afternoon": False,
            "sell_max_days": 4,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
        '接力-一进二弱转强:倒接力5': {
            "per_step_tick_gap": 2,
            "cold_start_steps": 5,
            "max_abserve_tick_steps": 510,
            "max_abserce_avg_price_down_steps": 5,
            "stop_profit_open_hc_pct": -0.09779748092115662,
            "dynamic_hc_stop_profit_thres": 1.8381341244144886,
            "last_close_price_hc_pct": -0.0019799207582651026,
            "last_day_sell_thres": 0.03472631351803903,
            "last_day_sell_huiche": 0.005615736270670137,
            "fd_mount": 65412589,
            "fd_vol_pct": 2.918552514926069e-06,
            "fd_ju_ticks": 29,
            "max_zb_times": 24,
            "stagnation_kline_ticks": 32,
            "decline_kline_ticks": 14,
            "yang_yin_threshold": 0.019206566084229795,
            "stagnation_n": 11,
            "stagnation_volume_ratio_threshold": 93.22369218405207,
            "stagnation_ratio_threshold": 771,
            "decline_volume_ratio_threshold": 100.0,
            "max_rebounds": 1,
            "decline_ratio_threshold": 1398,
            "flxd_ticks": 177,
            "flzz_ticks": 103,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": False,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": -0.015376845437306346,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": 0.009211580803393715,
            "open_price_max_hc": -0.007277140381827019,
            "loss_per_step_tick_gap": 11,
            "loss_cold_start_steps": 30,
            "loss_max_abserve_tick_steps": 302,
            "loss_max_abserce_avg_price_down_steps": 10,
            "loss_dynamic_hc_stop_profit_thres": 6.971211236955299,
            "loss_last_close_price_hc_pct": -0.07073985623680619,
            "loss_last_open_price_hc_pct": -0.0710138574161666,
            "loss_open_price_max_hc": -0.07932502702581883,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.001958021620746698,
            "day_zs_line": -0.13087730146369272,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 2,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
        '接力-一进二弱转强:倒接力31':{
            "per_step_tick_gap": 1,
            "cold_start_steps": 45,
            "max_abserve_tick_steps": 385,
            "max_abserce_avg_price_down_steps": 3,
            "stop_profit_open_hc_pct": -0.13615309678470672,
            "dynamic_hc_stop_profit_thres": 4.043163172236562,
            "last_close_price_hc_pct": -0.005965932680446158,
            "last_day_sell_thres": 0.1311974104495398,
            "last_day_sell_huiche": 0.014237431607868577,
            "fd_mount": 20192858,
            "fd_vol_pct": 0.6888893564952334,
            "fd_ju_ticks": 50,
            "max_zb_times": 20,
            "stagnation_kline_ticks": 19,
            "decline_kline_ticks": 17,
            "yang_yin_threshold": 0.02944726584363552,
            "stagnation_n": 21,
            "stagnation_volume_ratio_threshold": 65.17825666664703,
            "stagnation_ratio_threshold": 172,
            "decline_volume_ratio_threshold": 62.11620869057822,
            "max_rebounds": 7,
            "decline_ratio_threshold": 663,
            "flxd_ticks": 111,
            "flzz_ticks": 224,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": 0.06022472460958257,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": 0.009927200217467848,
            "open_price_max_hc": -0.09956760551146909,
            "loss_per_step_tick_gap": 1,
            "loss_cold_start_steps": 2,
            "loss_max_abserve_tick_steps": 79,
            "loss_max_abserce_avg_price_down_steps": 10,
            "loss_dynamic_hc_stop_profit_thres": 0.812141265825588,
            "loss_last_close_price_hc_pct": -0.042775079490827976,
            "loss_last_open_price_hc_pct": -0.007738604220134396,
            "loss_open_price_max_hc": -0.08981981966595437,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.005415923150372701,
            "day_zs_line": -0.01169359128424749,
            "sell_afternoon": False,
            "sell_half_afternoon": False,
            "sell_max_days": 4,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
        '接力-一进二弱转强:倒接力32':{
            "per_step_tick_gap": 1,
            "cold_start_steps": 7,
            "max_abserve_tick_steps": 515,
            "max_abserce_avg_price_down_steps": 1,
            "stop_profit_open_hc_pct": -0.03809888063595992,
            "dynamic_hc_stop_profit_thres": 1.3017089989235688,
            "last_close_price_hc_pct": -0.02935370684504273,
            "last_day_sell_thres": 0.7256933461364692,
            "last_day_sell_huiche": 0.002802732776876886,
            "fd_mount": 48977776,
            "fd_vol_pct": 0.0,
            "fd_ju_ticks": 3,
            "max_zb_times": 30,
            "stagnation_kline_ticks": 12,
            "decline_kline_ticks": 36,
            "yang_yin_threshold": 0.014729711628533803,
            "stagnation_n": 29,
            "stagnation_volume_ratio_threshold": 69.46011098054463,
            "stagnation_ratio_threshold": 230,
            "decline_volume_ratio_threshold": 19.94460358202636,
            "max_rebounds": 4,
            "decline_ratio_threshold": 324,
            "flxd_ticks": 331,
            "flzz_ticks": 159,
            "use_simiple_kline_strategy_flxd": False,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": 0.05247589688431628,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": 0.00028168103060647427,
            "open_price_max_hc": -0.0014179178075302535,
            "loss_per_step_tick_gap": 11,
            "loss_cold_start_steps": 4,
            "loss_max_abserve_tick_steps": 120,
            "loss_max_abserce_avg_price_down_steps": 10,
            "loss_dynamic_hc_stop_profit_thres": 0.8688691264239862,
            "loss_last_close_price_hc_pct": -0.0032723710719510506,
            "loss_last_open_price_hc_pct": -0.008191315036461056,
            "loss_open_price_max_hc": -0.013713604722146396,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.008974691469316424,
            "day_zs_line": -0.1364105726739229,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 4,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
        '接力-一进二弱转强:接力倒接力4':{
            "per_step_tick_gap": 1,
            "cold_start_steps": 6,
            "max_abserve_tick_steps": 394,
            "max_abserce_avg_price_down_steps": 2,
            "stop_profit_open_hc_pct": -0.031896128543757826,
            "dynamic_hc_stop_profit_thres": 4.571643321628637,
            "last_close_price_hc_pct": 0.009541368298678177,
            "last_day_sell_thres": 0.7150278915478029,
            "last_day_sell_huiche": 0.01579932775000117,
            "fd_mount": 109136712,
            "fd_vol_pct": 0.6871092711360351,
            "fd_ju_ticks": 1,
            "max_zb_times": 10,
            "stagnation_kline_ticks": 43,
            "decline_kline_ticks": 27,
            "yang_yin_threshold": 0.015967331980316236,
            "stagnation_n": 21,
            "stagnation_volume_ratio_threshold": 46.262976628904745,
            "stagnation_ratio_threshold": 257,
            "decline_volume_ratio_threshold": 66.13179943908548,
            "max_rebounds": 14,
            "decline_ratio_threshold": 1098,
            "flxd_ticks": 477,
            "flzz_ticks": 717,
            "use_simiple_kline_strategy_flxd": False,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": 0.03744281260880629,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.001186676298695681,
            "open_price_max_hc": -0.0012071027314360938,
            "loss_per_step_tick_gap": 20,
            "loss_cold_start_steps": 4,
            "loss_max_abserve_tick_steps": 18,
            "loss_max_abserce_avg_price_down_steps": 2,
            "loss_dynamic_hc_stop_profit_thres": 5.628555780021125,
            "loss_last_close_price_hc_pct": 0.009999999999999998,
            "loss_last_open_price_hc_pct": -0.0191463925606219,
            "loss_open_price_max_hc": -0.01988155372994392,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.004118487049116605,
            "day_zs_line": -0.10508094642302869,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 1,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
        '接力-一进二弱转强:接力倒接力3':{
                "per_step_tick_gap": 2,
                "cold_start_steps": 6,
                "max_abserve_tick_steps": 395,
                "max_abserce_avg_price_down_steps": 1,
                "stop_profit_open_hc_pct": -0.11749448106579258,
                "dynamic_hc_stop_profit_thres": 5.367781760582998,
                "last_close_price_hc_pct": 0.009999908884332949,
                "last_day_sell_thres": 0.43273765892974564,
                "last_day_sell_huiche": 0.0193847990165937,
                "fd_mount": 109394553,
                "fd_vol_pct": 0.741604676238952,
                "fd_ju_ticks": 1,
                "max_zb_times": 30,
                "stagnation_kline_ticks": 40,
                "decline_kline_ticks": 9,
                "yang_yin_threshold": 0.014759994512953869,
                "stagnation_n": 22,
                "stagnation_volume_ratio_threshold": 99.99999999999983,
                "stagnation_ratio_threshold": 864,
                "decline_volume_ratio_threshold": 67.60413271597422,
                "max_rebounds": 8,
                "decline_ratio_threshold": 727,
                "flxd_ticks": 364,
                "flzz_ticks": 1742,
                "use_simiple_kline_strategy_flxd": False,
                "use_simiple_kline_strategy_flzz": True,
                "flzz_use_smooth_price": True,
                "flzz_zf_thresh": 0.03422522038897473,
                "kline_sell_flxd_zy": True,
                "kline_sell_flxd_zs": False,
                "kline_sell_flzz_zs": True,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": -0.07569986331340088,
                "open_price_max_hc": -3.102737566931676e-07,
                "loss_per_step_tick_gap": 1,
                "loss_cold_start_steps": 3,
                "loss_max_abserve_tick_steps": 5,
                "loss_max_abserce_avg_price_down_steps": 1,
                "loss_dynamic_hc_stop_profit_thres": 0.8121272456935995,
                "loss_last_close_price_hc_pct": -0.003660432762837018,
                "loss_last_open_price_hc_pct": -0.06776813077983233,
                "loss_open_price_max_hc": -0.09562955271579619,
                "loss_down_open_sell_wait_time": True,
                "down_open_sell_wait_time": True,
                "day_zy_line": 0.004500679697372018,
                "day_zs_line": -0.0033324202669889726,
                "sell_afternoon": False,
                "sell_half_afternoon": True,
                "sell_max_days": 4,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '接力-一进二弱转强:接力倒接力31':{
                "per_step_tick_gap": 1,
                "cold_start_steps": 50,
                "max_abserve_tick_steps": 396,
                "max_abserce_avg_price_down_steps": 2,
                "stop_profit_open_hc_pct": -0.0003120146643211635,
                "dynamic_hc_stop_profit_thres": 1.3033472489702544,
                "last_close_price_hc_pct": 0.009999915022411885,
                "last_day_sell_thres": 0.18864062612033794,
                "last_day_sell_huiche": 0.0022557435182759284,
                "fd_mount": 148876010,
                "fd_vol_pct": 0.5210347645932725,
                "fd_ju_ticks": 1,
                "max_zb_times": 4,
                "stagnation_kline_ticks": 5,
                "decline_kline_ticks": 19,
                "yang_yin_threshold": 0.012002777255822812,
                "stagnation_n": 26,
                "stagnation_volume_ratio_threshold": 5.669041817977517,
                "stagnation_ratio_threshold": 52,
                "decline_volume_ratio_threshold": 5.764922766381721,
                "max_rebounds": 10,
                "decline_ratio_threshold": 1085,
                "flxd_ticks": 328,
                "flzz_ticks": 280,
                "use_simiple_kline_strategy_flxd": False,
                "use_simiple_kline_strategy_flzz": False,
                "flzz_use_smooth_price": True,
                "flzz_zf_thresh": -0.029696466302015338,
                "kline_sell_flxd_zy": False,
                "kline_sell_flxd_zs": True,
                "kline_sell_flzz_zs": True,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": -0.060653881155906364,
                "open_price_max_hc": 0.0,
                "loss_per_step_tick_gap": 25,
                "loss_cold_start_steps": 4,
                "loss_max_abserve_tick_steps": 433,
                "loss_max_abserce_avg_price_down_steps": 15,
                "loss_dynamic_hc_stop_profit_thres": 0.8501313537849571,
                "loss_last_close_price_hc_pct": -0.045459397884411924,
                "loss_last_open_price_hc_pct": 0.005087261273416553,
                "loss_open_price_max_hc": -0.07877204910232037,
                "loss_down_open_sell_wait_time": True,
                "down_open_sell_wait_time": True,
                "day_zy_line": 0.004108815401177096,
                "day_zs_line": -0.00694593751472356,
                "sell_afternoon": True,
                "sell_half_afternoon": False,
                "sell_max_days": 2,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '强更强:第一':{
                "per_step_tick_gap": 1,
                "cold_start_steps": 1,
                "max_abserve_tick_steps": 599,
                "max_abserce_avg_price_down_steps": 1,
                "stop_profit_open_hc_pct": -0.0030764758154217995,
                "dynamic_hc_stop_profit_thres": 4.531708361225206,
                "last_close_price_hc_pct": -0.02905437054272283,
                "last_day_sell_thres": 0.8384153851640129,
                "last_day_sell_huiche": 0.006196799090737125,
                "fd_mount": 121969316,
                "fd_vol_pct": 0.4356617833412199,
                "fd_ju_ticks": 1,
                "max_zb_times": 1,
                "stagnation_kline_ticks": 7,
                "decline_kline_ticks": 9,
                "yang_yin_threshold": 0.026263831712890456,
                "stagnation_n": 28,
                "stagnation_volume_ratio_threshold": 47.1294568144386,
                "stagnation_ratio_threshold": 1453,
                "decline_volume_ratio_threshold": 13.76197808126921,
                "max_rebounds": 9,
                "decline_ratio_threshold": 22,
                "flxd_ticks": 177,
                "flzz_ticks": 590,
                "use_simiple_kline_strategy_flxd": True,
                "use_simiple_kline_strategy_flzz": True,
                "flzz_use_smooth_price": False,
                "flzz_zf_thresh": 0.06590638344001651,
                "kline_sell_flxd_zy": True,
                "kline_sell_flxd_zs": True,
                "kline_sell_flzz_zs": False,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": 8.465920462168506e-05,
                "open_price_max_hc": -0.015757737008011766,
                "loss_per_step_tick_gap": 1,
                "loss_cold_start_steps": 3,
                "loss_max_abserve_tick_steps": 406,
                "loss_max_abserce_avg_price_down_steps": 2,
                "loss_dynamic_hc_stop_profit_thres": 0.811197238564801,
                "loss_last_close_price_hc_pct": -0.060982523622196125,
                "loss_last_open_price_hc_pct": -0.0076529620681949585,
                "loss_open_price_max_hc": -0.06764655435544471,
                "loss_down_open_sell_wait_time": False,
                "down_open_sell_wait_time": True,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-高强中低开低吸:强方向前2':{
                "per_step_tick_gap": 11,
                "cold_start_steps": 22,
                "max_abserve_tick_steps": 159,
                "max_abserce_avg_price_down_steps": 6,
                "stop_profit_open_hc_pct": -0.08877130010961737,
                "dynamic_hc_stop_profit_thres": 1.5551440910534233,
                "last_close_price_hc_pct": 0.00904442326252453,
                "last_day_sell_thres": 0.19936768015963496,
                "last_day_sell_huiche": 0.0024135004211861023,
                "fd_mount": 81429663,
                "fd_vol_pct": 0.49984843051505834,
                "fd_ju_ticks": 7,
                "max_zb_times": 25,
                "stagnation_kline_ticks": 16,
                "decline_kline_ticks": 5,
                "yang_yin_threshold": 0.0022474535460190064,
                "stagnation_n": 15,
                "stagnation_volume_ratio_threshold": 36.97649609846565,
                "stagnation_ratio_threshold": 298,
                "decline_volume_ratio_threshold": 15.00439283406275,
                "max_rebounds": 0,
                "decline_ratio_threshold": 81,
                "flxd_ticks": 490,
                "flzz_ticks": 1043,
                "use_simiple_kline_strategy_flxd": True,
                "use_simiple_kline_strategy_flzz": True,
                "flzz_use_smooth_price": True,
                "flzz_zf_thresh": -0.019324393939138144,
                "kline_sell_flxd_zy": True,
                "kline_sell_flxd_zs": True,
                "kline_sell_flzz_zs": False,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": 0.009207286167419407,
                "open_price_max_hc": -0.08980725552614663,
                "loss_per_step_tick_gap": 1,
                "loss_cold_start_steps": 1,
                "loss_max_abserve_tick_steps": 216,
                "loss_max_abserce_avg_price_down_steps": 1,
                "loss_dynamic_hc_stop_profit_thres": 7.060285489758057,
                "loss_last_close_price_hc_pct": -0.054885082285079455,
                "loss_last_open_price_hc_pct": -0.006892303797429984,
                "loss_open_price_max_hc": -0.012496595491574782,
                "loss_down_open_sell_wait_time": False,
                "down_open_sell_wait_time": True,
                "day_zy_line": 0.03291087567775239,
                "day_zs_line": -0.04726409163277622,
                "sell_afternoon": False,
                "sell_half_afternoon": True,
                "sell_max_days": 3,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-低位高强低吸:中低频2': {
                "per_step_tick_gap": 24,
                "cold_start_steps": 2,
                "max_abserve_tick_steps": 418,
                "max_abserce_avg_price_down_steps": 11,
                "stop_profit_open_hc_pct": -0.14556327455087165,
                "dynamic_hc_stop_profit_thres": 0.6249231437120463,
                "last_close_price_hc_pct": -0.008233067683012034,
                "last_day_sell_thres": 0.5550275544146134,
                "last_day_sell_huiche": 0.017007020307935505,
                "fd_mount": 70580988,
                "fd_vol_pct": 0.22180422218803342,
                "fd_ju_ticks": 1,
                "max_zb_times": 24,
                "stagnation_kline_ticks": 50,
                "decline_kline_ticks": 4,
                "yang_yin_threshold": 0.020572896407380813,
                "stagnation_n": 8,
                "stagnation_volume_ratio_threshold": 2.637445355649766,
                "stagnation_ratio_threshold": 913,
                "decline_volume_ratio_threshold": 66.69355005947185,
                "max_rebounds": 10,
                "decline_ratio_threshold": 777,
                "flxd_ticks": 51,
                "flzz_ticks": 1595,
                "use_simiple_kline_strategy_flxd": False,
                "use_simiple_kline_strategy_flzz": True,
                "flzz_use_smooth_price": False,
                "flzz_zf_thresh": 0.003184894585675318,
                "kline_sell_flxd_zy": True,
                "kline_sell_flxd_zs": False,
                "kline_sell_flzz_zs": True,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": -0.07706625587721513,
                "open_price_max_hc": -0.06978271355060414,
                "loss_per_step_tick_gap": 5,
                "loss_cold_start_steps": 2,
                "loss_max_abserve_tick_steps": 281,
                "loss_max_abserce_avg_price_down_steps": 3,
                "loss_dynamic_hc_stop_profit_thres": 7.360941735716625,
                "loss_last_close_price_hc_pct": 0.008571296155579352,
                "loss_last_open_price_hc_pct": -0.05855492518196858,
                "loss_open_price_max_hc": -0.09999964765079974,
                "loss_down_open_sell_wait_time": False,
                "down_open_sell_wait_time": True,
                "day_zy_line": 0.012194991420234237,
                "day_zs_line": -0.048238860141852385,
                "sell_afternoon": True,
                "sell_half_afternoon": False,
                "sell_max_days": 3,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-高强中低开低吸:强方向前1': {
                "per_step_tick_gap": 1,
                "cold_start_steps": 35,
                "max_abserve_tick_steps": 756,
                "max_abserce_avg_price_down_steps": 13,
                "stop_profit_open_hc_pct": -0.08289715169711272,
                "dynamic_hc_stop_profit_thres": 5.873626858342443,
                "last_close_price_hc_pct": -0.001059536800572279,
                "last_day_sell_thres": 0.9514681390116997,
                "last_day_sell_huiche": 0.01997115818116928,
                "fd_mount": 67656956,
                "fd_vol_pct": 0.7335172553948014,
                "fd_ju_ticks": 17,
                "max_zb_times": 26,
                "stagnation_kline_ticks": 33,
                "decline_kline_ticks": 33,
                "yang_yin_threshold": 0.002,
                "stagnation_n": 19,
                "stagnation_volume_ratio_threshold": 70.3039204520171,
                "stagnation_ratio_threshold": 403,
                "decline_volume_ratio_threshold": 2.6750113398904984,
                "max_rebounds": 12,
                "decline_ratio_threshold": 951,
                "flxd_ticks": 25,
                "flzz_ticks": 1862,
                "use_simiple_kline_strategy_flxd": True,
                "use_simiple_kline_strategy_flzz": True,
                "flzz_use_smooth_price": True,
                "flzz_zf_thresh": 0.02351603200443779,
                "kline_sell_flxd_zy": True,
                "kline_sell_flxd_zs": True,
                "kline_sell_flzz_zs": True,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": -0.07220555931236056,
                "open_price_max_hc": 0.0,
                "loss_per_step_tick_gap": 23,
                "loss_cold_start_steps": 4,
                "loss_max_abserve_tick_steps": 137,
                "loss_max_abserce_avg_price_down_steps": 5,
                "loss_dynamic_hc_stop_profit_thres": 6.157542225686702,
                "loss_last_close_price_hc_pct": 0.00842432222017839,
                "loss_last_open_price_hc_pct": -0.07305958580070385,
                "loss_open_price_max_hc": -0.04765865091598595,
                "loss_down_open_sell_wait_time": False,
                "down_open_sell_wait_time": False,
                "day_zy_line": 0.1190705263286383,
                "day_zs_line": -0.025177851049818817,
                "sell_afternoon": False,
                "sell_half_afternoon": True,
                "sell_max_days": 3,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-高强中低开低吸:强方向前11': {
                "per_step_tick_gap": 1,
                "cold_start_steps": 35,
                "max_abserve_tick_steps": 578,
                "max_abserce_avg_price_down_steps": 12,
                "stop_profit_open_hc_pct": -0.00021986904120092302,
                "dynamic_hc_stop_profit_thres": 7.720336486174417,
                "last_close_price_hc_pct": 0.009969871607601585,
                "last_day_sell_thres": 0.01,
                "last_day_sell_huiche": 0.011733947816293678,
                "fd_mount": 74456506,
                "fd_vol_pct": 0.4958307932442073,
                "fd_ju_ticks": 1,
                "max_zb_times": 1,
                "stagnation_kline_ticks": 3,
                "decline_kline_ticks": 37,
                "yang_yin_threshold": 0.011282743422100047,
                "stagnation_n": 11,
                "stagnation_volume_ratio_threshold": 5.376317865302129,
                "stagnation_ratio_threshold": 1310,
                "decline_volume_ratio_threshold": 34.95279773777804,
                "max_rebounds": 13,
                "decline_ratio_threshold": 1211,
                "flxd_ticks": 171,
                "flzz_ticks": 1609,
                "use_simiple_kline_strategy_flxd": False,
                "use_simiple_kline_strategy_flzz": False,
                "flzz_use_smooth_price": True,
                "flzz_zf_thresh": 0.09269022793101303,
                "kline_sell_flxd_zy": True,
                "kline_sell_flxd_zs": True,
                "kline_sell_flzz_zs": False,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": 0.01,
                "open_price_max_hc": -0.0001743476575550532,
                "loss_per_step_tick_gap": 1,
                "loss_cold_start_steps": 4,
                "loss_max_abserve_tick_steps": 485,
                "loss_max_abserce_avg_price_down_steps": 15,
                "loss_dynamic_hc_stop_profit_thres": 0.010000000000000002,
                "loss_last_close_price_hc_pct": 0.005364653283102305,
                "loss_last_open_price_hc_pct": -0.035787147173711925,
                "loss_open_price_max_hc": -0.03155697684621779,
                "loss_down_open_sell_wait_time": True,
                "down_open_sell_wait_time": False,
                "day_zy_line": 0.11941017138411761,
                "day_zs_line": -0.025430563451691778,
                "sell_afternoon": False,
                "sell_half_afternoon": False,
                "sell_max_days": 3,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-低位中强中低开低吸:第一高频': {
                "per_step_tick_gap": 13,
                "cold_start_steps": 43,
                "max_abserve_tick_steps": 907,
                "max_abserce_avg_price_down_steps": 15,
                "stop_profit_open_hc_pct": -0.022754518085340715,
                "dynamic_hc_stop_profit_thres": 1.4763635666879935,
                "last_close_price_hc_pct": -0.03177249244028102,
                "last_day_sell_thres": 0.5593422746060492,
                "last_day_sell_huiche": 0.02,
                "fd_mount": 63087595,
                "fd_vol_pct": 0.49775692458023624,
                "fd_ju_ticks": 1,
                "max_zb_times": 27,
                "stagnation_kline_ticks": 38,
                "decline_kline_ticks": 13,
                "yang_yin_threshold": 0.008468913474006363,
                "stagnation_n": 2,
                "stagnation_volume_ratio_threshold": 54.8434808808676,
                "stagnation_ratio_threshold": 914,
                "decline_volume_ratio_threshold": 33.762734665376904,
                "max_rebounds": 7,
                "decline_ratio_threshold": 1316,
                "flxd_ticks": 323,
                "flzz_ticks": 1091,
                "use_simiple_kline_strategy_flxd": True,
                "use_simiple_kline_strategy_flzz": True,
                "flzz_use_smooth_price": False,
                "flzz_zf_thresh": 0.017702261060721872,
                "kline_sell_flxd_zy": False,
                "kline_sell_flxd_zs": False,
                "kline_sell_flzz_zs": True,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": -0.04341254042938279,
                "open_price_max_hc": -0.07250223214593927,
                "loss_per_step_tick_gap": 15,
                "loss_cold_start_steps": 28,
                "loss_max_abserve_tick_steps": 47,
                "loss_max_abserce_avg_price_down_steps": 15,
                "loss_dynamic_hc_stop_profit_thres": 5.1068217967245975,
                "loss_last_close_price_hc_pct": -0.06731495250229769,
                "loss_last_open_price_hc_pct": -0.08,
                "loss_open_price_max_hc": -0.09255514751780936,
                "loss_down_open_sell_wait_time": False,
                "down_open_sell_wait_time": False,
                "day_zy_line": 0.0013897346733054783,
                "day_zs_line": -0.8423126604774431,
                "sell_afternoon": True,
                "sell_half_afternoon": False,
                "sell_max_days": 7,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-低位中强中低开低吸:第二高频': {
                "per_step_tick_gap": 20,
                "cold_start_steps": 0,
                "max_abserve_tick_steps": 463,
                "max_abserce_avg_price_down_steps": 14,
                "stop_profit_open_hc_pct": -0.09156828991184919,
                "dynamic_hc_stop_profit_thres": 1.5320330956540635,
                "last_close_price_hc_pct": -0.022182251093624934,
                "last_day_sell_thres": 0.2210028282774104,
                "last_day_sell_huiche": 0.0012491900130150093,
                "fd_mount": 27602410,
                "fd_vol_pct": 0.6075951721593746,
                "fd_ju_ticks": 1,
                "max_zb_times": 18,
                "stagnation_kline_ticks": 13,
                "decline_kline_ticks": 36,
                "yang_yin_threshold": 0.03,
                "stagnation_n": 2,
                "stagnation_volume_ratio_threshold": 75.35524090372232,
                "stagnation_ratio_threshold": 66,
                "decline_volume_ratio_threshold": 40.9689772141835,
                "max_rebounds": 12,
                "decline_ratio_threshold": 498,
                "flxd_ticks": 142,
                "flzz_ticks": 1085,
                "use_simiple_kline_strategy_flxd": False,
                "use_simiple_kline_strategy_flzz": True,
                "flzz_use_smooth_price": False,
                "flzz_zf_thresh": -0.05814755933476397,
                "kline_sell_flxd_zy": False,
                "kline_sell_flxd_zs": False,
                "kline_sell_flzz_zs": False,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": -0.005408809417351692,
                "open_price_max_hc": -0.03548253509526245,
                "loss_per_step_tick_gap": 6,
                "loss_cold_start_steps": 0,
                "loss_max_abserve_tick_steps": 334,
                "loss_max_abserce_avg_price_down_steps": 4,
                "loss_dynamic_hc_stop_profit_thres": 0.15727894644447377,
                "loss_last_close_price_hc_pct": -0.007189292118114406,
                "loss_last_open_price_hc_pct": -0.01819496971190171,
                "loss_open_price_max_hc": -0.062114322845860645,
                "loss_down_open_sell_wait_time": False,
                "down_open_sell_wait_time": True,
                "day_zy_line": 0.002675357039982913,
                "day_zs_line": -0.07769151414089057,
                "sell_afternoon": True,
                "sell_half_afternoon": False,
                "sell_max_days": 4,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-高强中低开低吸:方向前2': {
                "per_step_tick_gap": 14,
                "cold_start_steps": 21,
                "max_abserve_tick_steps": 688,
                "max_abserce_avg_price_down_steps": 5,
                "stop_profit_open_hc_pct": -0.14434534146133335,
                "dynamic_hc_stop_profit_thres": 0.34887566466390285,
                "last_close_price_hc_pct": 0.009900010439712198,
                "last_day_sell_thres": 0.9793077824922035,
                "last_day_sell_huiche": 0.008733069801992736,
                "fd_mount": 103280507,
                "fd_vol_pct": 0.461307975507421,
                "fd_ju_ticks": 1,
                "max_zb_times": 1,
                "stagnation_kline_ticks": 29,
                "decline_kline_ticks": 33,
                "yang_yin_threshold": 0.010029104499523307,
                "stagnation_n": 29,
                "stagnation_volume_ratio_threshold": 48.944807796888036,
                "stagnation_ratio_threshold": 597,
                "decline_volume_ratio_threshold": 19.196195133475022,
                "max_rebounds": 0,
                "decline_ratio_threshold": 909,
                "flxd_ticks": 348,
                "flzz_ticks": 855,
                "use_simiple_kline_strategy_flxd": True,
                "use_simiple_kline_strategy_flzz": False,
                "flzz_use_smooth_price": False,
                "flzz_zf_thresh": 0.09846866528869569,
                "kline_sell_flxd_zy": False,
                "kline_sell_flxd_zs": True,
                "kline_sell_flzz_zs": True,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": -0.017992408811599993,
                "open_price_max_hc": -0.0001556764463843429,
                "loss_per_step_tick_gap": 1,
                "loss_cold_start_steps": 1,
                "loss_max_abserve_tick_steps": 56,
                "loss_max_abserce_avg_price_down_steps": 12,
                "loss_dynamic_hc_stop_profit_thres": 0.010000000000000002,
                "loss_last_close_price_hc_pct": -0.04181789338891646,
                "loss_last_open_price_hc_pct": 0.009649778493764433,
                "loss_open_price_max_hc": -0.0006999835176486604,
                "loss_down_open_sell_wait_time": False,
                "down_open_sell_wait_time": False,
                "day_zy_line": 0.03271366441706974,
                "day_zs_line": -0.03630322411643912,
                "sell_afternoon": True,
                "sell_half_afternoon": True,
                "sell_max_days": 3,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-高强中低开低吸:方向前22': {
                "per_step_tick_gap": 1,
                "cold_start_steps": 32,
                "max_abserve_tick_steps": 939,
                "max_abserce_avg_price_down_steps": 2,
                "stop_profit_open_hc_pct": -0.0670933014343109,
                "dynamic_hc_stop_profit_thres": 2.917020519389309,
                "last_close_price_hc_pct": 0.009066832365539642,
                "last_day_sell_thres": 0.6513575584588506,
                "last_day_sell_huiche": 0.008527860007964634,
                "fd_mount": 112211570,
                "fd_vol_pct": 0.5821389713801058,
                "fd_ju_ticks": 9,
                "max_zb_times": 21,
                "stagnation_kline_ticks": 20,
                "decline_kline_ticks": 11,
                "yang_yin_threshold": 0.0163767023116175,
                "stagnation_n": 18,
                "stagnation_volume_ratio_threshold": 30.12150516432736,
                "stagnation_ratio_threshold": 1282,
                "decline_volume_ratio_threshold": 61.185607347188515,
                "max_rebounds": 8,
                "decline_ratio_threshold": 90,
                "flxd_ticks": 254,
                "flzz_ticks": 1161,
                "use_simiple_kline_strategy_flxd": False,
                "use_simiple_kline_strategy_flzz": True,
                "flzz_use_smooth_price": True,
                "flzz_zf_thresh": -0.02786222883750058,
                "kline_sell_flxd_zy": False,
                "kline_sell_flxd_zs": True,
                "kline_sell_flzz_zs": False,
                "kline_sell_flzz_zy": True,
                "last_open_price_hc_pct": -0.02606690426399076,
                "open_price_max_hc": -0.011367663661366639,
                "loss_per_step_tick_gap": 2,
                "loss_cold_start_steps": 1,
                "loss_max_abserve_tick_steps": 30,
                "loss_max_abserce_avg_price_down_steps": 2,
                "loss_dynamic_hc_stop_profit_thres": 0.010339332463797122,
                "loss_last_close_price_hc_pct": 0.0016935184831327762,
                "loss_last_open_price_hc_pct": -0.07677933757148317,
                "loss_open_price_max_hc": -0.06330451061908478,
                "loss_down_open_sell_wait_time": True,
                "down_open_sell_wait_time": False,
                "day_zy_line": 0.0342770870772451,
                "day_zs_line": -0.0398477565575983,
                "sell_afternoon": False,
                "sell_half_afternoon": True,
                "sell_max_days": 3,
                "stop_profit_pct": 0.0,
                "static_hc_stop_profit_pct": 1.0,
                "loss_static_hc_stop_profit_pct": 1.0
            },
        '低吸-首红断低吸:第一高频': {
            "per_step_tick_gap": 16,
            "cold_start_steps": 4,
            "max_abserve_tick_steps": 829,
            "max_abserce_avg_price_down_steps": 10,
            "stop_profit_open_hc_pct": -0.002850435144143261,
            "dynamic_hc_stop_profit_thres": 0.5862656709578017,
            "last_close_price_hc_pct": -0.03820308472819503,
            "last_day_sell_thres": 0.21731518911257364,
            "last_day_sell_huiche": 0.013461334931976852,
            "fd_mount": 36375145,
            "fd_vol_pct": 0.638250890273812,
            "fd_ju_ticks": 5,
            "max_zb_times": 2,
            "stagnation_kline_ticks": 38,
            "decline_kline_ticks": 48,
            "yang_yin_threshold": 0.0021139232493034366,
            "stagnation_n": 26,
            "stagnation_volume_ratio_threshold": 37.95404882959419,
            "stagnation_ratio_threshold": 688,
            "decline_volume_ratio_threshold": 81.66145284444677,
            "max_rebounds": 4,
            "decline_ratio_threshold": 1468,
            "flxd_ticks": 267,
            "flzz_ticks": 991,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": -0.008847071797489992,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": False,
            "last_open_price_hc_pct": -0.006555045038654269,
            "open_price_max_hc": -0.07958645661591879,
            "loss_per_step_tick_gap": 1,
            "loss_cold_start_steps": 0,
            "loss_max_abserve_tick_steps": 298,
            "loss_max_abserce_avg_price_down_steps": 7,
            "loss_dynamic_hc_stop_profit_thres": 0.5505881558458123,
            "loss_last_close_price_hc_pct": -0.060240407181819576,
            "loss_last_open_price_hc_pct": -0.0212662234889203,
            "loss_open_price_max_hc": -0.003036271395056148,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.005029501308747063,
            "day_zs_line": -0.11140574139868037,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 2,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-首红断低吸:第二高频': {
            "per_step_tick_gap": 13,
            "cold_start_steps": 20,
            "max_abserve_tick_steps": 938,
            "max_abserce_avg_price_down_steps": 7,
            "stop_profit_open_hc_pct": -0.0027353081350318434,
            "dynamic_hc_stop_profit_thres": 0.6013706338292539,
            "last_close_price_hc_pct": -0.03761245647986554,
            "last_day_sell_thres": 0.5205346765902945,
            "last_day_sell_huiche": 0.014781482579791231,
            "fd_mount": 42677175,
            "fd_vol_pct": 0.4181723815583741,
            "fd_ju_ticks": 44,
            "max_zb_times": 25,
            "stagnation_kline_ticks": 4,
            "decline_kline_ticks": 30,
            "yang_yin_threshold": 0.018985832261433848,
            "stagnation_n": 14,
            "stagnation_volume_ratio_threshold": 99.99829215257026,
            "stagnation_ratio_threshold": 1382,
            "decline_volume_ratio_threshold": 45.12608483836211,
            "max_rebounds": 13,
            "decline_ratio_threshold": 329,
            "flxd_ticks": 261,
            "flzz_ticks": 2000,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": False,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": 0.09767952388231449,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": False,
            "kline_sell_flzz_zy": False,
            "last_open_price_hc_pct": -0.005446449194498333,
            "open_price_max_hc": -0.08545249106922401,
            "loss_per_step_tick_gap": 17,
            "loss_cold_start_steps": 27,
            "loss_max_abserve_tick_steps": 497,
            "loss_max_abserce_avg_price_down_steps": 5,
            "loss_dynamic_hc_stop_profit_thres": 0.10208033699906673,
            "loss_last_close_price_hc_pct": -0.024749296595047578,
            "loss_last_open_price_hc_pct": -0.0466017243182672,
            "loss_open_price_max_hc": -0.04212453021344702,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.016747394251459685,
            "day_zs_line": -0.11130382714739091,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 3,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-低位孕线低吸:回撤小收益大': {
            "per_step_tick_gap": 3,
            "cold_start_steps": 0,
            "max_abserve_tick_steps": 665,
            "max_abserce_avg_price_down_steps": 10,
            "stop_profit_open_hc_pct": -0.10470649060659085,
            "dynamic_hc_stop_profit_thres": 1.783821832237422,
            "last_close_price_hc_pct": -0.03985115710332191,
            "last_day_sell_thres": 0.530730248793767,
            "last_day_sell_huiche": 0.009693000077103109,
            "fd_mount": 135292028,
            "fd_vol_pct": 0.286491695699503,
            "fd_ju_ticks": 4,
            "max_zb_times": 18,
            "stagnation_kline_ticks": 46,
            "decline_kline_ticks": 42,
            "yang_yin_threshold": 0.0036395018924217687,
            "stagnation_n": 25,
            "stagnation_volume_ratio_threshold": 75.22410236194513,
            "stagnation_ratio_threshold": 49,
            "decline_volume_ratio_threshold": 1.1,
            "max_rebounds": 12,
            "decline_ratio_threshold": 34,
            "flxd_ticks": 27,
            "flzz_ticks": 576,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": 0.07495770942918142,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": False,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.07744853329701563,
            "open_price_max_hc": -0.1,
            "loss_per_step_tick_gap": 1,
            "loss_cold_start_steps": 1,
            "loss_max_abserve_tick_steps": 5,
            "loss_max_abserce_avg_price_down_steps": 6,
            "loss_dynamic_hc_stop_profit_thres": 0.12693458816461012,
            "loss_last_close_price_hc_pct": 0.009936012822589713,
            "loss_last_open_price_hc_pct": 0.009193032686900228,
            "loss_open_price_max_hc": 0.0,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.09692534559230684,
            "day_zs_line": -3.725138613927525e-05,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 3,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-低位孕线低吸:回撤小收益大2': {
            "per_step_tick_gap": 9,
            "cold_start_steps": 50,
            "max_abserve_tick_steps": 134,
            "max_abserce_avg_price_down_steps": 3,
            "stop_profit_open_hc_pct": -0.14783199802802316,
            "dynamic_hc_stop_profit_thres": 3.9662098989378394,
            "last_close_price_hc_pct": 0.006537814969271131,
            "last_day_sell_thres": 0.7819028788629364,
            "last_day_sell_huiche": 0.010839549483800082,
            "fd_mount": 102633367,
            "fd_vol_pct": 0.7198582344419509,
            "fd_ju_ticks": 1,
            "max_zb_times": 4,
            "stagnation_kline_ticks": 26,
            "decline_kline_ticks": 32,
            "yang_yin_threshold": 0.008178697083951723,
            "stagnation_n": 2,
            "stagnation_volume_ratio_threshold": 14.682933994796636,
            "stagnation_ratio_threshold": 53,
            "decline_volume_ratio_threshold": 68.57253412268696,
            "max_rebounds": 0,
            "decline_ratio_threshold": 715,
            "flxd_ticks": 289,
            "flzz_ticks": 1619,
            "use_simiple_kline_strategy_flxd": False,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": -0.04529444431672158,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.008504176739500904,
            "open_price_max_hc": 0.0,
            "loss_per_step_tick_gap": 2,
            "loss_cold_start_steps": 0,
            "loss_max_abserve_tick_steps": 8,
            "loss_max_abserce_avg_price_down_steps": 6,
            "loss_dynamic_hc_stop_profit_thres": 4.820249705373641,
            "loss_last_close_price_hc_pct": 0.008531789397980175,
            "loss_last_open_price_hc_pct": 0.009382012918373855,
            "loss_open_price_max_hc": -5.660421602709849e-05,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.10103986237763647,
            "day_zs_line": -0.00028783295293710235,
            "sell_afternoon": False,
            "sell_half_afternoon": False,
            "sell_max_days": 1,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-启动低吸:第一高频': {
            "per_step_tick_gap": 20,
            "cold_start_steps": 10,
            "max_abserve_tick_steps": 952,
            "max_abserce_avg_price_down_steps": 15,
            "stop_profit_open_hc_pct": -0.021352574698912566,
            "dynamic_hc_stop_profit_thres": 3.521685728958423,
            "last_close_price_hc_pct": 0.009387074417089027,
            "last_day_sell_thres": 0.11535682767786551,
            "last_day_sell_huiche": 0.0038714821021270302,
            "fd_mount": 32264789,
            "fd_vol_pct": 0.6065546960216586,
            "fd_ju_ticks": 24,
            "max_zb_times": 16,
            "stagnation_kline_ticks": 16,
            "decline_kline_ticks": 37,
            "yang_yin_threshold": 0.01259592359115565,
            "stagnation_n": 21,
            "stagnation_volume_ratio_threshold": 22.40925630375213,
            "stagnation_ratio_threshold": 1044,
            "decline_volume_ratio_threshold": 100.0,
            "max_rebounds": 2,
            "decline_ratio_threshold": 1320,
            "flxd_ticks": 197,
            "flzz_ticks": 1705,
            "use_simiple_kline_strategy_flxd": False,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": -0.018986519713314234,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": 0.009999999999999998,
            "open_price_max_hc": -0.09970809450175569,
            "loss_per_step_tick_gap": 8,
            "loss_cold_start_steps": 0,
            "loss_max_abserve_tick_steps": 74,
            "loss_max_abserce_avg_price_down_steps": 1,
            "loss_dynamic_hc_stop_profit_thres": 0.010467494575666423,
            "loss_last_close_price_hc_pct": -0.03639054263771159,
            "loss_last_open_price_hc_pct": -0.07001252954152383,
            "loss_open_price_max_hc": -0.014442722859094568,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.0018364234454929613,
            "day_zs_line": -0.07642714994471639,
            "sell_afternoon": False,
            "sell_half_afternoon": False,
            "sell_max_days": 1,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-启动低吸:第一高频2': {
            "per_step_tick_gap": 23,
            "cold_start_steps": 35,
            "max_abserve_tick_steps": 950,
            "max_abserce_avg_price_down_steps": 12,
            "stop_profit_open_hc_pct": -0.04234760147948927,
            "dynamic_hc_stop_profit_thres": 0.9382732078669451,
            "last_close_price_hc_pct": -0.013220762531350457,
            "last_day_sell_thres": 0.9355957433854509,
            "last_day_sell_huiche": 0.005573860350171872,
            "fd_mount": 110835558,
            "fd_vol_pct": 0.6431895928756942,
            "fd_ju_ticks": 46,
            "max_zb_times": 29,
            "stagnation_kline_ticks": 15,
            "decline_kline_ticks": 48,
            "yang_yin_threshold": 0.029154666081377414,
            "stagnation_n": 26,
            "stagnation_volume_ratio_threshold": 35.38400252864047,
            "stagnation_ratio_threshold": 15,
            "decline_volume_ratio_threshold": 42.74031050795999,
            "max_rebounds": 7,
            "decline_ratio_threshold": 623,
            "flxd_ticks": 209,
            "flzz_ticks": 101,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": 0.026856918956079896,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": False,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.07761553753876924,
            "open_price_max_hc": -0.02165767763384082,
            "loss_per_step_tick_gap": 23,
            "loss_cold_start_steps": 0,
            "loss_max_abserve_tick_steps": 477,
            "loss_max_abserce_avg_price_down_steps": 1,
            "loss_dynamic_hc_stop_profit_thres": 0.010486817980092808,
            "loss_last_close_price_hc_pct": -0.02364816510082711,
            "loss_last_open_price_hc_pct": -0.075185140154202,
            "loss_open_price_max_hc": -0.08357328166376907,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.0,
            "day_zs_line": -0.07563701907809972,
            "sell_afternoon": True,
            "sell_half_afternoon": True,
            "sell_max_days": 1,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-低位断板低吸:第一高频': {
            "per_step_tick_gap": 8,
            "cold_start_steps": 48,
            "max_abserve_tick_steps": 614,
            "max_abserce_avg_price_down_steps": 6,
            "stop_profit_open_hc_pct": -0.1449770698665277,
            "dynamic_hc_stop_profit_thres": 0.11232403941422145,
            "last_close_price_hc_pct": 0.01,
            "last_day_sell_thres": 0.6824667478465597,
            "last_day_sell_huiche": 0.001,
            "fd_mount": 136821379,
            "fd_vol_pct": 0.7094178284954769,
            "fd_ju_ticks": 6,
            "max_zb_times": 19,
            "stagnation_kline_ticks": 37,
            "decline_kline_ticks": 10,
            "yang_yin_threshold": 0.0026743808104845246,
            "stagnation_n": 10,
            "stagnation_volume_ratio_threshold": 28.62823645156742,
            "stagnation_ratio_threshold": 1275,
            "decline_volume_ratio_threshold": 30.591835656075453,
            "max_rebounds": 3,
            "decline_ratio_threshold": 752,
            "flxd_ticks": 500,
            "flzz_ticks": 734,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": -0.07,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": False,
            "last_open_price_hc_pct": -0.03309886509436013,
            "open_price_max_hc": 0.0,
            "loss_per_step_tick_gap": 4,
            "loss_cold_start_steps": 5,
            "loss_max_abserve_tick_steps": 452,
            "loss_max_abserce_avg_price_down_steps": 8,
            "loss_dynamic_hc_stop_profit_thres": 4.739178533556185,
            "loss_last_close_price_hc_pct": -0.011082359164919502,
            "loss_last_open_price_hc_pct": -0.045825073533991026,
            "loss_open_price_max_hc": -0.05161366500104146,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.12111433031308273,
            "day_zs_line": -0.03396088839405979,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 1,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-低位断板低吸:第一高频2': {
            "per_step_tick_gap": 16,
            "cold_start_steps": 42,
            "max_abserve_tick_steps": 957,
            "max_abserce_avg_price_down_steps": 15,
            "stop_profit_open_hc_pct": -0.0565417708035179,
            "dynamic_hc_stop_profit_thres": 3.7162916522365634,
            "last_close_price_hc_pct": -0.036272974349435404,
            "last_day_sell_thres": 0.6297692715922535,
            "last_day_sell_huiche": 0.011761318304577963,
            "fd_mount": 110635005,
            "fd_vol_pct": 0.5567045816763891,
            "fd_ju_ticks": 1,
            "max_zb_times": 2,
            "stagnation_kline_ticks": 35,
            "decline_kline_ticks": 50,
            "yang_yin_threshold": 0.002,
            "stagnation_n": 11,
            "stagnation_volume_ratio_threshold": 67.97540850766607,
            "stagnation_ratio_threshold": 474,
            "decline_volume_ratio_threshold": 99.05704880160629,
            "max_rebounds": 1,
            "decline_ratio_threshold": 879,
            "flxd_ticks": 500,
            "flzz_ticks": 129,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": -0.014340446864659285,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.01534558718341639,
            "open_price_max_hc": -1.5169253746852008e-05,
            "loss_per_step_tick_gap": 3,
            "loss_cold_start_steps": 8,
            "loss_max_abserve_tick_steps": 423,
            "loss_max_abserce_avg_price_down_steps": 12,
            "loss_dynamic_hc_stop_profit_thres": 0.03166380730118515,
            "loss_last_close_price_hc_pct": -0.0676588629610073,
            "loss_last_open_price_hc_pct": -0.07080336492142411,
            "loss_open_price_max_hc": -0.00024131875321402183,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.012142354377989332,
            "day_zs_line": -0.12137965950008321,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 4,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '追涨-高强中高开追涨': {
            "per_step_tick_gap": 13,
            "cold_start_steps": 4,
            "max_abserve_tick_steps": 974,
            "max_abserce_avg_price_down_steps": 8,
            "stop_profit_open_hc_pct": -0.09637840260526367,
            "dynamic_hc_stop_profit_thres": 7.330450984842711,
            "last_close_price_hc_pct": -0.00302812583049597,
            "last_day_sell_thres": 0.011868315125632781,
            "last_day_sell_huiche": 0.008518038254702999,
            "fd_mount": 45569956,
            "fd_vol_pct": 2.0450387271788215e-11,
            "fd_ju_ticks": 44,
            "max_zb_times": 25,
            "stagnation_kline_ticks": 14,
            "decline_kline_ticks": 27,
            "yang_yin_threshold": 0.002046226751429945,
            "stagnation_n": 8,
            "stagnation_volume_ratio_threshold": 31.853606548782714,
            "stagnation_ratio_threshold": 33,
            "decline_volume_ratio_threshold": 75.69519645789191,
            "max_rebounds": 0,
            "decline_ratio_threshold": 865,
            "flxd_ticks": 131,
            "flzz_ticks": 448,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": 0.030764437929254915,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": 0.006211299314375581,
            "open_price_max_hc": -0.09898647628272106,
            "loss_per_step_tick_gap": 1,
            "loss_cold_start_steps": 0,
            "loss_max_abserve_tick_steps": 419,
            "loss_max_abserce_avg_price_down_steps": 14,
            "loss_dynamic_hc_stop_profit_thres": 0.5884486367799819,
            "loss_last_close_price_hc_pct": 0.00976166457408185,
            "loss_last_open_price_hc_pct": -0.07309642092903462,
            "loss_open_price_max_hc": -0.03654420480645671,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.005759608969959017,
            "day_zs_line": -0.0448297027442949,
            "sell_afternoon": False,
            "sell_half_afternoon": True,
            "sell_max_days": 4,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '追涨-小高开追涨:第一': {
            "per_step_tick_gap": 18,
            "cold_start_steps": 37,
            "max_abserve_tick_steps": 41,
            "max_abserce_avg_price_down_steps": 12,
            "stop_profit_open_hc_pct": -0.10145526753189926,
            "dynamic_hc_stop_profit_thres": 1.3964165590182316,
            "last_close_price_hc_pct": -0.0027201740445382608,
            "last_day_sell_thres": 0.9067878994380402,
            "last_day_sell_huiche": 0.013917407129705375,
            "fd_mount": 104624114,
            "fd_vol_pct": 0.0054602738132990365,
            "fd_ju_ticks": 25,
            "max_zb_times": 6,
            "stagnation_kline_ticks": 40,
            "decline_kline_ticks": 35,
            "yang_yin_threshold": 0.0029164644203467116,
            "stagnation_n": 23,
            "stagnation_volume_ratio_threshold": 24.15585357801191,
            "stagnation_ratio_threshold": 181,
            "decline_volume_ratio_threshold": 48.78661836930622,
            "max_rebounds": 15,
            "decline_ratio_threshold": 917,
            "flxd_ticks": 16,
            "flzz_ticks": 1380,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": False,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": 0.05289122098320788,
            "kline_sell_flxd_zy": True,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": False,
            "kline_sell_flzz_zy": False,
            "last_open_price_hc_pct": -0.06834525270312174,
            "open_price_max_hc": -0.04810030798205696,
            "loss_per_step_tick_gap": 23,
            "loss_cold_start_steps": 0,
            "loss_max_abserve_tick_steps": 491,
            "loss_max_abserce_avg_price_down_steps": 15,
            "loss_dynamic_hc_stop_profit_thres": 0.3216283879635703,
            "loss_last_close_price_hc_pct": -0.06177787755278756,
            "loss_last_open_price_hc_pct": -0.053898901603270905,
            "loss_open_price_max_hc": -0.05589698879215824,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.006669794140089128,
            "day_zs_line": -0.00026424512815437115,
            "sell_afternoon": False,
            "sell_half_afternoon": False,
            "sell_max_days": 2,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '追涨-小高开追涨:第二': {
            "per_step_tick_gap": 16,
            "cold_start_steps": 5,
            "max_abserve_tick_steps": 72,
            "max_abserce_avg_price_down_steps": 13,
            "stop_profit_open_hc_pct": -0.11891519758916003,
            "dynamic_hc_stop_profit_thres": 2.785135867856923,
            "last_close_price_hc_pct": 0.008171117255719666,
            "last_day_sell_thres": 1.0,
            "last_day_sell_huiche": 0.002848987174424115,
            "fd_mount": 110216580,
            "fd_vol_pct": 0.2040918078928599,
            "fd_ju_ticks": 50,
            "max_zb_times": 30,
            "stagnation_kline_ticks": 20,
            "decline_kline_ticks": 46,
            "yang_yin_threshold": 0.004819695767912378,
            "stagnation_n": 26,
            "stagnation_volume_ratio_threshold": 58.959852187007485,
            "stagnation_ratio_threshold": 409,
            "decline_volume_ratio_threshold": 77.09929605086326,
            "max_rebounds": 0,
            "decline_ratio_threshold": 1317,
            "flxd_ticks": 232,
            "flzz_ticks": 1765,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": -0.0631893136766011,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": False,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.01085920482366174,
            "open_price_max_hc": -0.0013507659696573842,
            "loss_per_step_tick_gap": 23,
            "loss_cold_start_steps": 18,
            "loss_max_abserve_tick_steps": 325,
            "loss_max_abserce_avg_price_down_steps": 10,
            "loss_dynamic_hc_stop_profit_thres": 2.4086330877407307,
            "loss_last_close_price_hc_pct": -0.06573464231422325,
            "loss_last_open_price_hc_pct": -0.0023262093848375014,
            "loss_open_price_max_hc": 0.0,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.0026839176509704044,
            "day_zs_line": -0.2500881471296623,
            "sell_afternoon": False,
            "sell_half_afternoon": False,
            "sell_max_days": 1,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-中位小低开低吸': {
            "per_step_tick_gap": 1,
            "cold_start_steps": 0,
            "max_abserve_tick_steps": 838,
            "max_abserce_avg_price_down_steps": 2,
            "stop_profit_open_hc_pct": -0.00812259541201604,
            "dynamic_hc_stop_profit_thres": 0.010692713326932791,
            "last_close_price_hc_pct": 0.009839980198561086,
            "last_day_sell_thres": 0.9721538003669161,
            "last_day_sell_huiche": 0.014429192969935922,
            "fd_mount": 84697344,
            "fd_vol_pct": 0.6503264412470761,
            "fd_ju_ticks": 17,
            "max_zb_times": 25,
            "stagnation_kline_ticks": 4,
            "decline_kline_ticks": 32,
            "yang_yin_threshold": 0.013150349591399027,
            "stagnation_n": 26,
            "stagnation_volume_ratio_threshold": 3.474543008508515,
            "stagnation_ratio_threshold": 16,
            "decline_volume_ratio_threshold": 38.665044151925855,
            "max_rebounds": 2,
            "decline_ratio_threshold": 1500,
            "flxd_ticks": 500,
            "flzz_ticks": 1377,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": -0.028075713309227195,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": True,
            "last_open_price_hc_pct": -0.006028057062141878,
            "open_price_max_hc": -0.0013760402776091482,
            "loss_per_step_tick_gap": 10,
            "loss_cold_start_steps": 3,
            "loss_max_abserve_tick_steps": 344,
            "loss_max_abserce_avg_price_down_steps": 9,
            "loss_dynamic_hc_stop_profit_thres": 2.1154194050271236,
            "loss_last_close_price_hc_pct": -0.07737676108640475,
            "loss_last_open_price_hc_pct": -0.018620932514337663,
            "loss_open_price_max_hc": -0.020681395443488907,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": False,
            "day_zy_line": 0.08620053278340647,
            "day_zs_line": -0.10526060446172225,
            "sell_afternoon": False,
            "sell_half_afternoon": True,
            "sell_max_days": 3,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '低吸-中位中强小低开低吸:第二高频': {
            "per_step_tick_gap": 15,
            "cold_start_steps": 30,
            "max_abserve_tick_steps": 267,
            "max_abserce_avg_price_down_steps": 11,
            "stop_profit_open_hc_pct": -0.1323743557469863,
            "dynamic_hc_stop_profit_thres": 3.8683351506172112,
            "last_close_price_hc_pct": -0.010949400739614696,
            "last_day_sell_thres": 0.6572873738297137,
            "last_day_sell_huiche": 0.004570378536209046,
            "fd_mount": 68224484,
            "fd_vol_pct": 0.6348096197672634,
            "fd_ju_ticks": 15,
            "max_zb_times": 18,
            "stagnation_kline_ticks": 48,
            "decline_kline_ticks": 25,
            "yang_yin_threshold": 0.026442009169563806,
            "stagnation_n": 24,
            "stagnation_volume_ratio_threshold": 52.17736411052479,
            "stagnation_ratio_threshold": 740,
            "decline_volume_ratio_threshold": 9.417024640133093,
            "max_rebounds": 5,
            "decline_ratio_threshold": 457,
            "flxd_ticks": 205,
            "flzz_ticks": 1471,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": True,
            "flzz_zf_thresh": 0.05066331520963483,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": False,
            "last_open_price_hc_pct": -0.005253735577482365,
            "open_price_max_hc": -0.08796521547633179,
            "loss_per_step_tick_gap": 10,
            "loss_cold_start_steps": 3,
            "loss_max_abserve_tick_steps": 381,
            "loss_max_abserce_avg_price_down_steps": 14,
            "loss_dynamic_hc_stop_profit_thres": 6.177075383085461,
            "loss_last_close_price_hc_pct": -0.03748823754656959,
            "loss_last_open_price_hc_pct": -0.05390628510640784,
            "loss_open_price_max_hc": -0.03643808828208933,
            "loss_down_open_sell_wait_time": False,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.9999834157012604,
            "day_zs_line": -0.010762575810320908,
            "sell_afternoon": False,
            "sell_half_afternoon": False,
            "sell_max_days": 4,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
}

from collections import deque

class SmoothFilter:
    def __init__(self, window_size=10):
        self.window = deque(maxlen=window_size)  # 滑动窗口
        self.smoothed_value = 0
        
    def update(self, new_value):
        self.window.append(new_value)
        self.smoothed_value = sum(self.window)/len(self.window)
        return self.smoothed_value

class StockMonitor(object):
    def __init__(self, stock_code, stock_name, qmt_trader = None, mkt_datas = None):
        # self.config = {}
        self.monitor_configs = {}
        # self.config['step_tick_gap'] = 5
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.mkt_datas = mkt_datas
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
        if mkt_datas and 'pre_avg_volumes' in mkt_datas:
            self.pre_avg_volumes = mkt_datas['pre_avg_volumes']
        else:
            self.pre_avg_volumes = []
        if not self.pre_avg_volumes:
            logger.error(f"[StockMonitor] 股票{self.stock_code} {self.stock_name} 没有前一日平均成交量")

        if qmt_trader != None:
            self.qmt_trader = qmt_trader
        self.strategy_to_kline_strategy = {}
        self.open_status = -1
        self.end = False
        self.pre_volume = -1
        self.cur_volume = -1
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
        # 炸板次数
        self.zb_times = 0

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
        # 当天涨停价
        self.limit_up_price = -1
        # 当天跌停价
        self.limit_down_price = -1

        self.limit_up_tick_times = -1
        # 已经卖出rowid
        self.selled_row_ids = []
        # 准备卖出的rowid
        self.to_sell_row_ids = []
        # 剩余未卖出
        self.left_row_ids = []

        self.bq = queue.Queue()
        self.row_id_to_monitor_data = {}

        self.monitor_type_to_row_ids = {}

        self.running_monitor_status = {}
        self.running_monitor_stock_status = {}

        self.running_monitor_down_status = {}

        self.running_monitor_observe_steps = {}
        self.strategy_to_row_ids = {}

        self.init_kline_strategies()

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
                if strategy_name not in self.strategy_to_row_ids:
                    self.strategy_to_row_ids[strategy_name] = []
                if row_id not in self.strategy_to_row_ids[strategy_name]:
                    self.strategy_to_row_ids[strategy_name].append(row_id)
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
                if strategy_name not in self.monitor_configs:
                    monitor_config = db.query_data_dict(monitor_config_table, condition_dict= {'strategy_name': strategy_name})
                    default_monitor_config = db.query_data_dict(monitor_config_table, condition_dict= {'strategy_name': 'default'})
                    if not monitor_config and not default_monitor_config:
                        logger.error(f"monitor_config null. {strategy_name}")
                        continue
                    if not monitor_config:
                        monitor_config = default_monitor_config
                    monitor_config = monitor_config[0]
                    self.monitor_configs[strategy_name] = monitor_config
                # if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                #     pass
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
        

        # self.config = config
        # self.db_name = config['db_name']
        # self.table_name = config['table_name']
    def start_monitor(self):
        logger.info(f"start monitor {self.stock_code} {self.stock_name}")
        self.thread = threading.Thread(target=self.monitor)
        self.thread.setDaemon(True)
        self.thread.start()
        return self.thread
    

    def stop_monitor(self):
        logger.info(f"stop monitor {self.stock_code} {self.stock_name}")
        self.thread.join()
    

    def init_kline_strategies(self):
        for strategy_name, params in strategy_to_params_configs.items():
            if params:
                self.monitor_configs[strategy_name] = params
                stagnation_kline_ticks = params.get('stagnation_kline_ticks', 10)
                decline_kline_ticks = params.get('decline_kline_ticks', 15)
                yang_yin_threshold = params.get('yang_yin_threshold', 0.002)
                stagnation_n = params.get('stagnation_n', 10)
                stagnation_volume_ratio_threshold = params.get('stagnation_volume_ratio_threshold', 2.5)
                stagnation_ratio_threshold = params.get('stagnation_ratio_threshold', 40)
                decline_volume_ratio_threshold = params.get('decline_volume_ratio_threshold', 2.5)
                max_rebounds = params.get('max_rebounds', 2)
                decline_ratio_threshold = params.get('decline_ratio_threshold', 50)
                use_simiple_kline_strategy = params.get('use_simiple_kline_strategy', True)
                use_simiple_kline_strategy_flxd = params.get('use_simiple_kline_strategy_flxd', False)
                use_simiple_kline_strategy_flzz = params.get('use_simiple_kline_strategy_flzz', False)
                flxd_ticks = params.get('flxd_ticks', 110)
                flzz_ticks = params.get('flzz_ticks', 5000)
                kline_sell_only_zy = params.get('kline_sell_only_zy', False)
                flzz_use_smooth_price = params.get('flzz_use_smooth_price', False)
                flzz_zf_thresh = params.get('flzz_zf_thresh', 0.03)
            else:
                stagnation_kline_ticks = 10
                decline_kline_ticks = 15
                yang_yin_threshold = 0.002
                stagnation_n = 10
                stagnation_volume_ratio_threshold = 2.5
                stagnation_ratio_threshold = 40
                decline_volume_ratio_threshold = 2.5
                max_rebounds = 2
                decline_ratio_threshold = 50
                use_simiple_kline_strategy = True
                use_simiple_kline_strategy_flxd = False
                use_simiple_kline_strategy_flzz = False
                flxd_ticks = 110
                flzz_ticks = 5000
                kline_sell_only_zy = False
                flzz_use_smooth_price = False
                flzz_zf_thresh = 0.03
            if use_simiple_kline_strategy and (use_simiple_kline_strategy_flxd or use_simiple_kline_strategy_flzz):
                kline_strategy = SimplifiedKLineStrategy(stagnation_kline_ticks = stagnation_kline_ticks, 
                                                          decline_kline_ticks = decline_kline_ticks, 
                                                          yang_yin_threshold = yang_yin_threshold, 
                                                          stagnation_n = stagnation_n, 
                                                          stagnation_volume_ratio_threshold = stagnation_volume_ratio_threshold, 
                                                          stagnation_ratio_threshold = stagnation_ratio_threshold, 
                                                          decline_volume_ratio_threshold = decline_volume_ratio_threshold, 
                                                          max_rebounds = max_rebounds, 
                                                          decline_ratio_threshold = decline_ratio_threshold)
                self.strategy_to_kline_strategy[strategy_name] = kline_strategy


    def monitor(self):
        while True:
            if not self.left_row_ids:
                logger.error(f"{self.stock_code}-{self.stock_name} 没有需要监控的卖出任务")
                self.end = True
                break
            data = self.bq.get()
            start_time = tm.time() * 1000
            if data is None:
                end_time = tm.time() * 1000
                elapsed_time = end_time - start_time
                logger.info(f"[StockMonitor] {self.stock_code} - {self.stock_name} monitor循环耗时: {elapsed_time:.2f}ms (无数据)")
                continue
            # m = {}
            time = data['time']
            lastPrice = data['lastPrice']
            open = data['open']
            high = data['high']
            low = data['low']
            lastClose = data['lastClose']
            volume = data['volume']
            if self.pre_volume == -1:
                self.pre_volume = volume
            
            amount = data['amount']
            pvolume = data['pvolume'] if data['pvolume'] > 0 else 1
            askPrice = data['askPrice']
            bidPrice = data['bidPrice']
            askVol = data['askVol']
            bidVol = data['bidVol']
            
            diff = calculate_seconds_difference(time)
            if diff > 10:
                logger.error(f"time diff > 10s. {diff} {time} {self.stock_code} {self.stock_name}")
                self.pre_volume = volume
                continue
            if self.open_status == -1:
                self.open_status = constants.OpenStatus.DOWN_OPEN if open <= lastClose else constants.OpenStatus.UP_OPEN
            if amount <= 0 or volume <= 0:
                logger.error(f"amount <= 0. {amount} {time} {self.stock_code} {self.stock_name}")
                continue
            if lastPrice <= 0:
                logger.error(f"lastPrice <= 0. {lastPrice} {time} {self.stock_code} {self.stock_name}")
                self.pre_volume = volume
                continue
            if self.pre_volume != -1 and volume >= self.pre_volume:
                self.cur_volume = volume - self.pre_volume
            else:
                self.cur_volume = 0  # 或者使用其他默认值
                logger.warning(f"成交量异常: current={volume}, previous={self.pre_volume}")
            self.pre_volume = volume
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

            logger.info(
                f"股票代码： {self.stock_code}, 股票名称： {self.stock_name}, "
                f"均价: {self.avg_price:.2f}, 当前价: {self.current_price:.2f}, 开盘价: {self.open_price:.2f}, "
                f"昨天收盘价: {self.last_close_price:.2f}, 当前步数: {self.current_tick_steps}, "
                f"当前天内涨幅: {self.current_open_increase:.2%}, 当天涨幅: {self.current_increase:.2%}, "
                f"当天最高价: {self.current_max_price:.2f}, 当天最低价: {self.current_min_price:.2f}, "
                f"当天天内最高涨幅: {self.current_max_open_increase:.2%}, 当天天内最低涨幅: {self.current_min_open_increase:.2%}, "
                f"当天最高涨幅: {self.current_max_increase:.2%}, 当天最低涨幅: {self.current_min_increase:.2%}"
            )

            if self.strategy_to_kline_strategy:

                for strategy, kline_strategy in self.strategy_to_kline_strategy.items():
                    if strategy not in self.strategy_to_row_ids:
                        continue

                    all_row_ids = self.strategy_to_row_ids[strategy]
                    if not all_row_ids:
                        continue

                    c_params = self.monitor_configs[strategy]
                    flzz_use_smooth_price = c_params.get("flzz_use_smooth_price", False)
                    use_simiple_kline_strategy_flxd = c_params.get("use_simiple_kline_strategy_flxd", False)
                    use_simiple_kline_strategy_flzz = c_params.get("use_simiple_kline_strategy_flzz", False)

                    use_simiple_kline_strategy = c_params.get("use_simiple_kline_strategy", True)
                    flxd_ticks = c_params.get("flxd_ticks", 110)
                    kline_sell_only_zy = c_params.get("kline_sell_only_zy", False)
                    kline_sell_flxd_zy = c_params.get("kline_sell_flxd_zy", False)
                    kline_sell_flxd_zs = c_params.get("kline_sell_flxd_zs", False)
                    kline_sell_flzz_zs = c_params.get("kline_sell_flzz_zs", False)
                    kline_sell_flzz_zy = c_params.get("kline_sell_flzz_zy", False)

                    flzz_ticks = c_params.get("flzz_ticks", 5000)
                    flzz_zf_thresh = c_params.get("flzz_zf_thresh", 0.03)

                    cur_prevolume = self.pre_avg_volumes[self.current_tick_steps] if self.current_tick_steps < len(self.pre_avg_volumes) else 0

                    logger.info(f"[StockMonitor]cur_prevolume: {cur_prevolume}, cur_volume: {self.cur_volume}, cur_tick: {self.current_tick_steps}, cur_code: {self.stock_code}")

                    if flzz_use_smooth_price:
                        kline_strategy.update_tick_data(self.cur_volume, self.smooth_current_price, cur_prevolume, self.avg_price)
                    else:
                        kline_strategy.update_tick_data(self.cur_volume, self.current_price, cur_prevolume, self.avg_price)
                    stagnation_signal, decline_signal = kline_strategy.generate_signals()

                    if use_simiple_kline_strategy_flxd and use_simiple_kline_strategy and self.current_tick_steps <= flxd_ticks and decline_signal:
                        for row_id in all_row_ids:
                            monitor_data = self.row_id_to_monitor_data[row_id]
                            monitor_type = monitor_data['monitor_type']
                            if monitor_type == 1 and kline_sell_flxd_zy:
                                self.add_to_sell(row_id)
                            if monitor_type == 2 and kline_sell_flxd_zs:
                                self.add_to_sell(row_id)


                    if use_simiple_kline_strategy_flzz and use_simiple_kline_strategy and self.current_tick_steps <= flzz_ticks and stagnation_signal and self.current_increase >= flzz_zf_thresh:
                        for row_id in all_row_ids:
                            monitor_data = self.row_id_to_monitor_data[row_id]
                            monitor_type = monitor_data['monitor_type']
                            if monitor_type == 1 and kline_sell_flzz_zy:
                                self.add_to_sell(row_id)
                            if monitor_type == 2 and kline_sell_flzz_zs:
                                self.add_to_sell(row_id)


            if self.limit_up_price < 0 or self.limit_down_price < 0:
                limit_down_price_0, limit_up_price_0 = constants.get_limit_price(self.last_close_price, stock_code=self.stock_code)
                self.limit_up_price = limit_up_price_0
                self.limit_down_price = limit_down_price_0

            if self.limit_up_price > 0 and abs(self.smooth_current_price - self.limit_up_price) < 0.0033:
                if not bidPrice or not bidVol:
                    self.sell_all(price = self.current_price)
                    continue
                self.max_limit_up_vol = max(self.max_limit_up_vol, bidVol[0])

                buy1_price = bidPrice[0]
                buy1_vol = bidVol[0]
                # if abs(buy1_price - self.limit_up_price) >= 0.01:
                #     if buy1_price > 0:
                #         self.sell_all(price = buy1_price)
                #     else:
                #         self.sell_all(price = self.current_price)
                #     continue
                
                if self.limit_up_status:
                    self.limit_up_tick_times = self.limit_up_tick_times + 1
                    if self.limit_up_tick_times > 1:
                        if not bidPrice or not bidVol:
                            self.sell_all(price = self.current_price)
                            continue
                        buy1_price = bidPrice[0]
                        buy1_vol = bidVol[0]
                        if abs(buy1_price - self.limit_up_price) >= 0.01:
                            if buy1_price > 0:
                                self.sell_all(price = buy1_price)
                            else:
                                self.sell_all(price = self.current_price)
                            continue
                        # 封单金额过小 卖
                        if buy1_price * buy1_vol * 100 < 60000000 and buy1_vol / self.max_limit_up_vol < 0.5:
                            logger.info(f"封单金额过小，卖出 {self.stock_code} {self.stock_name}")
                            if buy1_price > 0:
                                self.sell_all(price = buy1_price)
                            else:
                                self.sell_all(price = self.current_price)
                            continue
                else:
                    self.limit_up_tick_times = 0
                    self.limit_up_status = True

            elif self.limit_up_price > 0 and abs(self.smooth_current_price - self.limit_up_price) >= 0.0033:
                self.max_limit_up_vol = -1
                
                if self.limit_up_status:
                    # 涨停炸板卖
                    self.zb_times = self.zb_times + 1
                    if self.zb_times > 1:
                        logger.info(f"炸板了，卖出 {self.stock_code} {self.stock_name}")
                        if not bidPrice or not bidVol:
                            self.sell_all(price = self.current_price)
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
                                    self.sell_all(price = buy2_price)
                                else:
                                    if buy1_price > 0:
                                        self.sell_all(price = buy1_price)
                                    else:
                                        self.sell_all(price = self.current_price)
                            else:
                                if buy1_price > 0:
                                    self.sell_all(price = buy1_price)
                                else:
                                    self.sell_all(price = self.current_price)
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
            
            for monitor_type, row_ids in self.monitor_type_to_row_ids.items():
                if not row_ids:
                    continue
                if monitor_type == constants.STOP_PROFIT_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        if row_id in self.to_sell_row_ids:
                            continue

                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        origin_trade_price = monitor_data['origin_trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']
                        if strategy_name not in self.monitor_configs:
                            logger.error(f"策略{strategy_name} 无配置 跳过")
                            if row_id not in self.selled_row_ids:
                                self.selled_row_ids.append(row_id)
                            if row_id in self.left_row_ids:
                                self.left_row_ids.remove(row_id)
                            continue
                        monitor_config = self.monitor_configs[strategy_name]
                        # tick的gap间隔
                        per_step_tick_gap = monitor_config['per_step_tick_gap']
                        # 等待冷启动次数
                        cold_start_steps = monitor_config['cold_start_steps']
                        # 最大观察的tick数量
                        max_abserve_tick_steps = monitor_config['max_abserve_tick_steps']
                        # 跌落均线下观察的tick数量
                        max_abserce_avg_price_down_steps = monitor_config['max_abserce_avg_price_down_steps']
                        # 止盈的开盘最大下跌
                        stop_profit_open_hc_pct = monitor_config['stop_profit_open_hc_pct']
                        # 止盈的最小止盈点
                        stop_profit_pct = monitor_config['stop_profit_pct']
                        # 动态回撤的系数
                        dynamic_hc_stop_profit_thres = monitor_config['dynamic_hc_stop_profit_thres']
                        # 静态回撤的幅度
                        static_hc_stop_profit_pct = monitor_config['static_hc_stop_profit_pct']
                        # 前一天收盘价的水下容忍比例
                        last_close_price_hc_pct = monitor_config['last_close_price_hc_pct']

                        last_open_price_hc_pct = monitor_config['last_open_price_hc_pct']

                        open_price_max_hc = monitor_config['open_price_max_hc']

                        if 'down_open_sell_wait_time' in monitor_config:
                            down_open_sell_wait_time = monitor_config['down_open_sell_wait_time']
                        else:
                            down_open_sell_wait_time = False

                        # 动态止盈线
                        dynamic_zs_line = -1
                        # 静态止盈线
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
                            # if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                            #     self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                
                            # elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                            #     self.running_monitor_status[strategy_name] = constants.StockStatus.UP_LOW_AVG_DOWN
                                
                            # elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                            #     self.running_monitor_status[strategy_name] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                
                            # elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                            #     self.running_monitor_status[strategy_name] = constants.StockStatus.UP_HIGH_AVG_UP
                            
                            # if self.current_price <= self.avg_price:
                            #     self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_DOWN
                            # else:
                            #     self.running_monitor_stock_status[strategy_name] = constants.StockStatus.AVG_UP
                            
                            # self.running_monitor_down_status[strategy_name] = False
                            # self.running_monitor_observe_steps[strategy_name] = 0

                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")

                            if self.current_price <= self.avg_price:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")
                            else:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")

                            self.running_monitor_down_status[row_id] = False
                            self.running_monitor_observe_steps[row_id] = 0
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_down_status 更新为 {self.running_monitor_down_status[row_id]}")
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_observe_steps 更新为 {self.running_monitor_observe_steps[row_id]}")

                        elif self.current_tick_steps > cold_start_steps:
                            if self.current_tick_steps % per_step_tick_gap == 0:
                                # 低开低走
                                if self.running_monitor_status[row_id] == constants.StockStatus.DOWN_LOW_AVG_DOWN:

                                    if self.smooth_current_price < zs_line and self.smooth_current_price <= self.avg_price:
                                        if self.limit_down_status:
                                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                                        else:
                                            if self.current_tick_steps < max_abserve_tick_steps:
                                                # 5min内增加一定的容忍性
                                                if self.smooth_current_price < self.ma5:
                                                    
                                                    logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                            else:
                                                logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                    # 均线下
                                    if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                                        
                                        if self.smooth_current_price <= self.avg_price:
                                            if self.running_monitor_down_status[row_id]:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                                    if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
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
                                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                                            else:
                                                if self.current_tick_steps < max_abserve_tick_steps:
                                                    # 5min内增加一定的容忍性
                                                    if self.smooth_current_price < self.ma5:
                                                        
                                                        logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                                else:
                                                    logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                        if self.current_price <= self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN

                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[row_id] = True
                                            self.running_monitor_observe_steps[row_id] = 0
                                        elif self.current_price > self.avg_price and self.current_price <= self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                            self.running_monitor_down_status[row_id] = True
                                            self.running_monitor_observe_steps[row_id] = 0

                                elif self.running_monitor_status[row_id] == constants.StockStatus.DOWN_HIGH_AVG_UP:
                                    if self.smooth_current_price < zs_line and self.smooth_current_price <= self.avg_price:
                                        if self.limit_down_status:
                                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 跌停了，等5min后卖，先不出售")
                                        else:
                                            if self.current_tick_steps < max_abserve_tick_steps:
                                                # 5min内增加一定的容忍性
                                                if self.smooth_current_price < self.ma5:
                                                    
                                                    logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                            else:
                                                logger.info(f"低于止损线 止盈卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
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
                                                logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈线 超过回撤卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
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
                                                        logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
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
                                            logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
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
                                            logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                
                                                if self.running_monitor_down_status[row_id]:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                                        if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                            logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                            self.add_to_sell(row_id=row_id)
                                                            continue
                                                else:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue

                                            else:
                                                if self.current_price <= self.open_price * (1 + last_open_price_hc_pct) and (self.current_tick_steps >= max_abserve_tick_steps or not down_open_sell_wait_time):

                                                    logger.info(f"跌破开盘价卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
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
                                            logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
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
                                            logger.info(f"跌破收盘价卖. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                
                                                if self.running_monitor_down_status[row_id]:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                                        if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                            logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                            self.add_to_sell(row_id=row_id)
                                                            continue
                                                else:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue

                                            else:
                                                if self.current_price <= self.open_price * (1 + last_open_price_hc_pct) and (self.current_tick_steps >= max_abserve_tick_steps or not down_open_sell_wait_time):
                                                    logger.info(f"跌破开盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
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
                                        
                            # else:
                            #     now = datetime.datetime.now().time()
                            #     target_time = datetime.time(11, 25)
                            #     if now > target_time:
                            #         logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 超过最大时间卖出")
                            #         self.add_to_sell(row_id=row_id)
                    
                elif monitor_type == constants.STOP_LOSS_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        if row_id in self.to_sell_row_ids:
                            continue
                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']

                        if strategy_name not in self.monitor_configs:
                            logger.error(f"策略{strategy_name} 无配置 跳过")
                            if row_id not in self.selled_row_ids:
                                self.selled_row_ids.append(row_id)
                            if row_id in self.left_row_ids:
                                self.left_row_ids.remove(row_id)
                            continue
                        monitor_config = self.monitor_configs[strategy_name]
                        per_step_tick_gap = monitor_config['loss_per_step_tick_gap']
                        cold_start_steps = monitor_config['loss_cold_start_steps']
                        max_abserve_tick_steps = monitor_config['loss_max_abserve_tick_steps']
                        max_abserce_avg_price_down_steps = monitor_config['loss_max_abserce_avg_price_down_steps']
                        
                        dynamic_hc_stop_profit_thres = monitor_config['loss_dynamic_hc_stop_profit_thres']
                        static_hc_stop_profit_pct = monitor_config['loss_static_hc_stop_profit_pct']
                        last_close_price_hc_pct = monitor_config['loss_last_close_price_hc_pct']
                        last_open_price_hc_pct = monitor_config['loss_last_open_price_hc_pct']
                        open_price_max_hc = monitor_config['loss_open_price_max_hc']

                        if 'loss_down_open_sell_wait_time' in monitor_config:
                            down_open_sell_wait_time = monitor_config['loss_down_open_sell_wait_time']
                        else:
                            down_open_sell_wait_time = False


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

                        logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 动态止盈线: {dynamic_zs_line:.2f}, 静态止盈线: {static_zs_line:.2f}")

                        if self.current_tick_steps < cold_start_steps:
                            continue
                        elif self.current_tick_steps == cold_start_steps:
                            
                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_LOW_AVG_DOWN
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price <= self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_LOW_AVG_DOWN
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")
                            elif self.current_price > self.open_price and self.open_status == constants.OpenStatus.UP_OPEN:
                                self.running_monitor_status[row_id] = constants.StockStatus.UP_HIGH_AVG_UP
                                monitor_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_status 更新为 {monitor_status_name}")

                            if self.current_price <= self.avg_price:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")
                            else:
                                self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                stock_status_name = [attr for attr in dir(constants.StockStatus) if getattr(constants.StockStatus, attr) == self.running_monitor_stock_status[row_id]][0]
                                logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_stock_status 更新为 {stock_status_name}")

                            if self.current_price <= self.open_price and self.open_status == constants.OpenStatus.DOWN_OPEN:
                                if not self.limit_down_status:
                                    # 直接割
                                    logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                    self.add_to_sell(row_id=row_id)
                                    continue

                            self.running_monitor_down_status[row_id] = False
                            self.running_monitor_observe_steps[row_id] = 0
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_down_status 更新为 {self.running_monitor_down_status[row_id]}")
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} running_monitor_observe_steps 更新为 {self.running_monitor_observe_steps[row_id]}")
                            
                        elif self.current_tick_steps > cold_start_steps:
                            if self.current_tick_steps % per_step_tick_gap == 0:
                                if self.running_monitor_status[row_id] == constants.StockStatus.DOWN_LOW_AVG_DOWN:
                                    if self.smooth_current_price <= self.open_price and self.smooth_current_price <= self.avg_price:

                                        if not self.limit_down_status:
                                            # 直接割
                                            logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                    
                                    if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_DOWN:
                                        
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                        elif self.current_price <= self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_DOWN
                                            
                                            if self.running_monitor_down_status[row_id]:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                                    if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                        logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
                                            
                                    elif self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                                        
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
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
                                            logger.info(f"止损低走直接割，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
                                    if self.running_monitor_stock_status[row_id] == constants.StockStatus.AVG_UP:
                                        if self.current_price > self.avg_price and self.current_price > self.open_price:
                                            self.running_monitor_status[row_id] = constants.StockStatus.DOWN_HIGH_AVG_UP
                                            self.running_monitor_stock_status[row_id] = constants.StockStatus.AVG_UP
                                            if dynamic_zs_line > 0 and self.current_price <= dynamic_zs_line:
                                                logger.info(f"动态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {dynamic_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
                                            if static_zs_line > 0 and self.current_price <= static_zs_line:
                                                logger.info(f"静态止盈，卖出. {self.stock_code} {self.stock_name} {strategy_name} {static_zs_line} {self.current_price} {current_time_str}")
                                                self.add_to_sell(row_id=row_id)
                                                continue
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
                                                        logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.current_tick_steps >= max_abserve_tick_steps:
                                                    logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
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
                                            logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
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
                                            logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                
                                                if self.running_monitor_down_status[row_id]:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                                        if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                            logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                            self.add_to_sell(row_id=row_id)
                                                            continue
                                                else:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.smooth_current_price <= self.open_price * (1 + last_open_price_hc_pct) and (self.current_tick_steps >= max_abserve_tick_steps or not down_open_sell_wait_time):

                                                    logger.info(f"跌破开盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
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
                                            logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue
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
                                            logger.info(f"破昨天收盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                            self.add_to_sell(row_id=row_id)
                                            continue

                                        if self.current_price <= self.avg_price:
                                            if self.open_price > self.avg_price:
                                                
                                                if self.running_monitor_down_status[row_id]:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        self.running_monitor_observe_steps[row_id] = self.running_monitor_observe_steps[row_id] + 1
                                                        if self.running_monitor_observe_steps[row_id] >= max_abserce_avg_price_down_steps:
                                                            logger.info(f"跌入均线下超时未反弹，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                            self.add_to_sell(row_id=row_id)
                                                            continue
                                                else:
                                                    if self.current_tick_steps >= max_abserve_tick_steps:
                                                        logger.info(f"最大观察时间到，还在均线下，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                        self.add_to_sell(row_id=row_id)
                                                        continue
                                            else:
                                                if self.smooth_current_price <= self.open_price * (1 + last_open_price_hc_pct) and (self.current_tick_steps >= max_abserve_tick_steps or not down_open_sell_wait_time):
                                                    logger.info(f"跌破开盘价，卖出. {self.stock_code} {self.stock_name} {strategy_name} {self.current_price} {current_time_str}")
                                                    self.add_to_sell(row_id=row_id)
                                                    continue
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
                                        
                            # else:
                            #     now = datetime.datetime.now().time()
                            #     target_time = datetime.time(11, 25)
                            #     if now > target_time:
                            #         logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 超过最大时间卖出")
                            #         self.add_to_sell(row_id=row_id)
                            #     pass
                elif monitor_type ==  constants.LAST_TRADE_DAY_TRADE_TYPE:
                    for row_id in row_ids:
                        if row_id in self.selled_row_ids:
                            continue
                        if row_id in self.to_sell_row_ids:
                            continue
                        monitor_data = self.row_id_to_monitor_data[row_id]
                        strategy_name = monitor_data['strategy_name']
                        trade_price = monitor_data['trade_price']
                        limit_down_price = monitor_data['limit_down_price']
                        limit_up_price = monitor_data['limit_up_price']
                        if strategy_name not in self.monitor_configs:
                            logger.error(f"策略{strategy_name} 无配置 跳过")
                            if row_id not in self.selled_row_ids:
                                self.selled_row_ids.append(row_id)
                            if row_id in self.left_row_ids:
                                self.left_row_ids.remove(row_id)
                            continue
                        monitor_config = self.monitor_configs[strategy_name]
                        per_step_tick_gap = monitor_config['per_step_tick_gap']
                        cold_start_steps = monitor_config['cold_start_steps']
                        max_abserve_tick_steps = monitor_config['max_abserve_tick_steps']
                        max_abserce_avg_price_down_steps = monitor_config['max_abserce_avg_price_down_steps']
                        last_day_sell_thres = monitor_config['last_day_sell_thres']
                        last_day_sell_huiche = monitor_config['last_day_sell_huiche']

                        max_thres_line = self.smooth_current_max_price * (1 - last_day_sell_huiche)
                        if self.current_increase > last_day_sell_thres and self.current_price < max_thres_line:
                            logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 回撤卖出")
                            self.add_to_sell(row_id=row_id)
                            continue
                        # now = datetime.datetime.now().time()
                        # target_time = datetime.time(11, 25)
                        # if now > target_time:
                        #     logger.info(f"股票 {self.stock_code} {self.stock_name} 策略 {strategy_name} 超过最大时间卖出")
                        #     self.add_to_sell(row_id=row_id)

            
            if not bidPrice or not bidVol:
                self.sell_all_row_ids(price = self.current_price)
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
                        self.sell_all_row_ids(price = buy2_price)
                    else:
                        if buy1_price > 0:
                            self.sell_all_row_ids(price = buy1_price)
                        else:
                            self.sell_all_row_ids(price = self.current_price)
                else:
                    if buy1_price > 0:
                        self.sell_all_row_ids(price = buy1_price)
                    else:
                        self.sell_all_row_ids(price = self.current_price)
            end_time = tm.time() * 1000
            elapsed_time = end_time - start_time
            logger.info(f"[StockMonitor] {self.stock_code} - {self.stock_name} monitor循环耗时: {elapsed_time:.2f}ms")


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
        if not self.to_sell_row_ids:
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
        temp_to_sell_row_ids = self.to_sell_row_ids[:]  # 复制一份避免修改影响遍历
        self.to_sell_row_ids.clear()  # 先清空，未卖出的会重新加回
        
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
            
            # 准备卖出信息
            strategy_name = data_dict['strategy_name']
            trade_price = data_dict['trade_price']
            origin_row_id = data_dict['origin_row_id']
            current_trade_days = data_dict['current_trade_days']
            
            # 记录实际卖出量
            extra_infos.append((
                self.stock_code, 
                can_sell,  # 实际卖出量
                trade_price, 
                origin_row_id, 
                strategy_name, 
                current_trade_days,
                'max_days', 
                can_sell  # 实际卖出量
            ))
            
            # 检查是否完全卖出
            if data_dict['left_volume'] == 0:
                self.selled_row_ids.append(row_id)
                if row_id in self.left_row_ids:
                    self.left_row_ids.remove(row_id)
                logger.debug(f"完全卖出 row_id={row_id}, 数量={can_sell}")
            else:
                logger.info(f"部分卖出 row_id={row_id}, 卖出={can_sell}, 剩余={data_dict['left_volume']}")
        
        if all_volume > 0:
            logger.info(f"执行卖出 {self.stock_code} {self.stock_name} 总量={all_volume} 价格={price}")
            if self.qmt_trader is not None:
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
        # 获取可用持仓量
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
        
        # 创建临时列表用于安全遍历
        temp_row_ids = list(self.row_id_to_monitor_data.keys())
        
        for row_id in temp_row_ids:
            # 检查可用量是否已用完
            if all_volume >= available_qty:
                break
                
            data_dict = self.row_id_to_monitor_data.get(row_id)
            if not data_dict:
                continue
                
            left_volume = data_dict.get('left_volume', 0)
            # 跳过已卖出或无效的数量
            if left_volume <= 0 or row_id in self.selled_row_ids:
                continue
                
            # 计算本次实际可卖出量
            can_sell = min(left_volume, available_qty - all_volume)
            
            # 更新持仓数据
            data_dict['left_volume'] = left_volume - can_sell
            all_volume += can_sell
            
            # 准备卖出信息
            strategy_name = data_dict.get('strategy_name', '')
            trade_price = data_dict.get('trade_price', 0.0)
            origin_row_id = data_dict.get('origin_row_id', '')
            current_trade_days = data_dict.get('current_trade_days', 0)
            
            # 记录实际卖出量
            extra_infos.append((
                self.stock_code, 
                can_sell,  # 实际卖出量
                trade_price, 
                origin_row_id, 
                strategy_name, 
                current_trade_days,
                'max_days', 
                can_sell  # 实际卖出量
            ))
            
            # 检查是否完全卖出
            if data_dict['left_volume'] == 0:
                self.selled_row_ids.append(row_id)
                if row_id in self.left_row_ids:
                    self.left_row_ids.remove(row_id)
                logger.debug(f"完全卖出 row_id={row_id}, 数量={can_sell}")
            else:
                logger.info(f"部分卖出 row_id={row_id}, 卖出={can_sell}, 剩余={data_dict['left_volume']}")
        
        if all_volume > 0:
            logger.info(f"执行全部卖出 {self.stock_code} {self.stock_name} 总量={all_volume} 价格={price}")
            if self.qmt_trader is not None:
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