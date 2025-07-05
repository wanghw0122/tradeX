import sqlite3
from datetime import datetime
from logger import logger

db_name = r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db'
from functools import partial

class SQLiteManager:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_table(self, table_name, columns):
        column_definitions = ', '.join([f"{col} {col_type}" for col, col_type in columns.items()])
        unique_constraint = "UNIQUE (date_key, strategy_name, sub_strategy_name, stock_code)"
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions}, {unique_constraint})"
        self.cursor.execute(create_table_query)
        self.conn.commit()

    def insert_data(self, table_name, data_dict):
        columns = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?' for _ in data_dict])
        values = tuple(data_dict.values())
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.cursor.execute(insert_query, values)
        self.conn.commit()
        logger.info("Data inserted successfully.")
        return self.cursor.lastrowid

    def insert_or_update_data(self, table_name, data_dict):
        columns = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?' for _ in data_dict])
        values = tuple(data_dict.values())
        insert_query = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.cursor.execute(insert_query, values)
        self.conn.commit()
        logger.info("Data inserted or updated successfully.")

    def delete_data(self, table_name, condition_dict):
        conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
        values = tuple(condition_dict.values())
        delete_query = f"DELETE FROM {table_name} WHERE {conditions}"
        self.cursor.execute(delete_query, values)
        self.conn.commit()
        logger.info("Data deleted successfully.")

    def update_data(self, table_name, update_dict, condition_dict):
        set_clause = ', '.join([f"{key} = ?" for key in update_dict])
        conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
        values = tuple(update_dict.values()) + tuple(condition_dict.values())
        update_query = f"UPDATE {table_name} SET {set_clause} WHERE {conditions}"
        self.cursor.execute(update_query, values)
        self.conn.commit()
        logger.info("Data updated successfully.")

    # def query_limit_up_records_by_date(self, input_date):
    #     """
    #     根据输入的日期查询 limit_up_strategy_info 表中日期在 date_key 和 last_date_key 之间的记录。

    #     :param input_date: 输入的日期，格式为 yyyy-mm-dd
    #     :return: 查询结果列表
    #     """
    #     query = "SELECT * FROM limit_up_strategy_info WHERE? BETWEEN date_key AND last_date_key"
    #     self.cursor.execute(query, (input_date,))
    #     return self.cursor.fetchall()
    
    def query_limit_up_records_by_date(self, input_date):
        """
        根据输入的日期查询 limit_up_strategy_info 表中日期在 date_key 和 last_date_key 之间的记录。

        :param input_date: 输入的日期，格式为 yyyy-mm-dd
        :return: 查询结果列表，每个元素为以列名为键的字典
        """
        query = "SELECT * FROM limit_up_strategy_info WHERE ? BETWEEN date_key AND last_date_key"
        self.cursor.execute(query, (input_date,))
        # 获取列名
        column_names = [description[0] for description in self.cursor.description]
        # 将查询结果转换为字典列表
        results = []
        for row in self.cursor.fetchall():
            row_dict = dict(zip(column_names, row))
            results.append(row_dict)
        return results

    def query_data(self, table_name, condition_dict=None, columns="*"):
        """
        查询指定表的数据
        :param table_name: 要查询的表名
        :param condition_dict: 查询条件，字典形式，键为列名，值为查询值
        :param columns: 要查询的列，默认为所有列
        :return: 查询结果列表
        """
        if condition_dict:
            conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
            values = tuple(condition_dict.values())
            query = f"SELECT {columns} FROM {table_name} WHERE {conditions}"
        else:
            query = f"SELECT {columns} FROM {table_name}"
            values = ()
        self.cursor.execute(query, values)
        return self.cursor.fetchall()
    
    def query_data_dict(self, table_name, condition_dict=None, columns="*"):
        """
        查询指定表的数据
        :param table_name: 要查询的表名
        :param condition_dict: 查询条件，字典形式，键为列名，值为查询值
        :param columns: 要查询的列，默认为所有列
        :return: 查询结果列表，每个元素为以列名为键的字典
        """
        if condition_dict:
            conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
            values = tuple(condition_dict.values())
            query = f"SELECT {columns} FROM {table_name} WHERE {conditions}"
        else:
            query = f"SELECT {columns} FROM {table_name}"
            values = ()
        self.cursor.execute(query, values)
        # 获取列名
        column_names = [description[0] for description in self.cursor.description]
        # 将查询结果转换为字典列表
        results = []
        for row in self.cursor.fetchall():
            row_dict = dict(zip(column_names, row))
            results.append(row_dict)
        return results

    def drop_table(self, table_name):
        drop_table_query = f"DROP TABLE IF EXISTS {table_name}"
        self.cursor.execute(drop_table_query)
        self.conn.commit()
        logger.info(f"Table {table_name} dropped successfully.")


    def update_budget(self, strategy_name, increment):
        import json
        from datetime import datetime
        try:
            self.conn.execute('BEGIN TRANSACTION')
            self.cursor.execute('SELECT id, budget, extra_info FROM strategy_budget WHERE strategy_name =?', (strategy_name,))
            result = self.cursor.fetchone()

            if result:
                budget_id, current_budget, extra_info_str = result
                new_budget = current_budget + increment
                try:
                    extra_info = json.loads(extra_info_str) if extra_info_str else []
                except json.JSONDecodeError:
                    extra_info = []
                update_info = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "amount": increment
                }
                extra_info.append(update_info)

                new_extra_info_str = json.dumps(extra_info)

                self.cursor.execute('UPDATE strategy_budget SET budget =?, extra_info =? WHERE id =?',
                            (new_budget, new_extra_info_str, budget_id))

                self.conn.commit()
                return 1
            else:
                self.conn.rollback()
                return -1

        except Exception as e:
            self.conn.rollback()
            return 0


    def batch_insert_data(self, table_name, data_list):
        """
        批量插入数据
        :param table_name: 要插入数据的表名
        :param data_list: 数据列表，每个元素为一个字典，代表一行数据
        """
        if not data_list:
            return
        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['?' for _ in data_list[0]])
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        values = [tuple(data.values()) for data in data_list]
        self.cursor.executemany(insert_query, values)
        self.conn.commit()
        logger.info("Batch data inserted successfully.")
    
    def batch_insert_data_by_date(self, datekey, data_list, prefix = "strategy_data_premarket_", strategy = None):
        """
        批量插入数据
        :param table_name: 要插入数据的表名
        :param data_list: 数据列表，每个元素为一个字典，代表一行数据
        """
        n_datekey = datekey
        if '-' in n_datekey:
            n_datekey = n_datekey.replace('-', '')
        n_datekey = n_datekey[:6]
        table_name = prefix + n_datekey
        if not data_list:
            return
        default_values = {
            'block_category': '',
            'block_codes': '',
            'industry_code': '',
            'max_block_category_rank': -1,
            'max_block_code_rank': -1,
            'max_industry_code_rank': -1,
            'is_bottom': 0,
            'is_broken_plate': 0,
            'is_down_broken': 0,
            'is_fall': 0,
            'is_first_down_broken': 0,
            'is_first_up_broken': 0,
            'is_gestation_line': 0,
            'is_half': 0,
            'is_high': 0,
            'is_highest': 0,
            'is_long_shadow': 0,
            'is_low': 0,
            'is_medium': 0,
            'is_meso': 0,
            'is_plummet': 0,
            'is_pre_st': 0,
            'is_small_high_open': 0,
            'is_up_broken': 0,
            'is_weak': 0,
            'first_limit_up_days': 0,
            'jsjl': 0.0,
            'cjs': 0.0,
            'xcjw': 0.0,
            'jssb': 0.0,
            'open_pct_rate': -100.0,
            'open_price': -1,
            'close_price': -1,
            'pre_close_price': -1,
            'next_day_open_price': -1,
            'next_day_close_price': -1,
            'next_day_high_price_open_10mins': -1,
            'next_day_low_price_open_10mins': -1,
            'next_day_high_price': -1,
            'next_day_low_price': -1,
            'in_premarket': 0,
            'in_premarket_match': 0,
            'mod_code': '',
            'mod_name': '',
            'mod_short_line_score': -100,
            'mod_short_line_score_change': -100,
            'mod_short_line_rank': -1,
            'mod_trend_score': -100,
            'mod_trend_score_change': -100,
            'mod_trend_rank': -1,
            'env_json_info': '',
            'block_category_info': '',
            # add
            "xcjw_v2": 0.0,
            "jssb_v2": 0.0,
            "cjs_v2": 0.0,
            "is_strength_high": 0,
            "is_strength_middle": 0,
            "is_strength_low": 0,
            "is_strength_increase": 0,
            "is_strength_reduct": 0,
            "short_line_score": 0.0,
            "short_line_score_change": 0.0,
            "jsjl_block": 0.0,
            "jssb_block": 0.0,
            "cjs_block": 0.0,
            "direction_cjs_v2": 0.0,
            "circulation_market_value": 0.0,
            "cgyk": "",
            "htyk": "",
            "cgyk_value": 0.0,
            "htyk_value": 0.0,
            "is_middle_high_open": 0,
            "is_large_high_open": 0,
            "is_small_low_open": 0,
            "is_middle_low_open": 0,
            "is_large_low_open": 0,
        }

        for data in data_list:
            for key, value in default_values.items():
                if key not in data:
                    data[key] = value
        try:
            self.conn.execute('BEGIN')
            keys = [k for k, _ in data_list[0].items()]
            columns = ', '.join(keys)
            placeholders = ', '.join(['?' for _ in data_list[0]])
            insert_query = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
            values = []
            for data in data_list:
                data_values = []
                for key in keys:
                    data_values.append(data[key])
                values.append(tuple(data_values))
            self.cursor.executemany(insert_query, values)
            # 提交事务
            self.conn.execute('COMMIT')
            logger.info(f"Batch data inserted or update successfully. strategy-{strategy}. date-{datekey}")
        except Exception as e:
            # 回滚事务
            self.conn.execute('ROLLBACK')
            logger.error(f"Batch data insertion or update failed: {e}, stretegy-{strategy}. date-{datekey}")

    def batch_delete_data(self, table_name, condition_list):
        """
        批量删除数据
        :param table_name: 要删除数据的表名
        :param condition_list: 条件列表，每个元素为一个字典，代表一组删除条件
        """
        if not condition_list:
            return
        for condition_dict in condition_list:
            conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
            values = tuple(condition_dict.values())
            delete_query = f"DELETE FROM {table_name} WHERE {conditions}"
            self.cursor.execute(delete_query, values)
        self.conn.commit()
        logger.info("Batch data deleted successfully.")

    def batch_update_data(self, table_name, update_condition_list):
        """
        批量更新数据
        :param table_name: 要更新数据的表名
        :param update_condition_list: 列表，每个元素为一个元组，元组第一个元素为更新字典，第二个元素为条件字典
        """
        if not update_condition_list:
            return
        for update_dict, condition_dict in update_condition_list:
            set_clause = ', '.join([f"{key} = ?" for key in update_dict])
            conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
            values = tuple(update_dict.values()) + tuple(condition_dict.values())
            update_query = f"UPDATE {table_name} SET {set_clause} WHERE {conditions}"
            self.cursor.execute(update_query, values)
        self.conn.commit()
        logger.info("Batch data updated successfully.")


    def batch_query_data(self, table_name, condition_list, columns="*"):
        """
        批量查询数据
        :param table_name: 要查询数据的表名
        :param condition_list: 条件列表，每个元素为一个字典，代表一组查询条件
        :param columns: 要查询的列，默认为所有列
        :return: 查询结果列表，每个元素为以列名为键的字典
        """
        all_results = []
        for condition_dict in condition_list:
            if condition_dict:
                conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
                values = tuple(condition_dict.values())
                query = f"SELECT {columns} FROM {table_name} WHERE {conditions}"
            else:
                query = f"SELECT {columns} FROM {table_name}"
                values = ()
            self.cursor.execute(query, values)
            # 获取列名
            column_names = [description[0] for description in self.cursor.description]
            # 将查询结果转换为字典列表
            results = []
            for row in self.cursor.fetchall():
                row_dict = dict(zip(column_names, row))
                results.append(row_dict)
            all_results.extend(results)
        return all_results

def create_strategy_table(prefix = "strategy_data_premarket_", specified_date = datetime.now().strftime("%Y%m")):
    # 表名
    table_name = prefix + specified_date
    columns = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "date_key": "TEXT NOT NULL",
        "strategy_name": "TEXT NOT NULL",
        "sub_strategy_name": "TEXT DEFAULT ''",
        "stock_code": "TEXT NOT NULL",
        "stock_name": "TEXT DEFAULT ''",
        "stock_rank": "INTEGER DEFAULT -1",
        "block_category": "TEXT DEFAULT ''",
        "block_codes": "TEXT DEFAULT ''",
        "industry_code": "TEXT DEFAULT ''",
        "max_block_category_rank": "INTEGER DEFAULT -1",
        "max_block_code_rank": "INTEGER DEFAULT -1",
        "max_industry_code_rank": "INTEGER DEFAULT -1",
        "is_bottom": "INTEGER CHECK (is_bottom IN (0, 1)) DEFAULT 0",
        "is_broken_plate": "INTEGER CHECK (is_broken_plate IN (0, 1)) DEFAULT 0",
        "is_down_broken": "INTEGER CHECK (is_down_broken IN (0, 1)) DEFAULT 0",
        "is_fall": "INTEGER CHECK (is_fall IN (0, 1)) DEFAULT 0",
        "is_first_down_broken": "INTEGER CHECK (is_first_down_broken IN (0, 1)) DEFAULT 0",
        "is_first_up_broken": "INTEGER CHECK (is_first_up_broken IN (0, 1)) DEFAULT 0",
        "is_gestation_line": "INTEGER CHECK (is_gestation_line IN (0, 1)) DEFAULT 0",
        "is_half": "INTEGER CHECK (is_half IN (0, 1)) DEFAULT 0",
        "is_high": "INTEGER CHECK (is_high IN (0, 1)) DEFAULT 0",
        "is_highest": "INTEGER CHECK (is_highest IN (0, 1)) DEFAULT 0",
        "is_long_shadow": "INTEGER CHECK (is_long_shadow IN (0, 1)) DEFAULT 0",
        "is_low": "INTEGER CHECK (is_low IN (0, 1)) DEFAULT 0",
        "is_medium": "INTEGER CHECK (is_medium IN (0, 1)) DEFAULT 0",
        "is_meso": "INTEGER CHECK (is_meso IN (0, 1)) DEFAULT 0",
        "is_plummet": "INTEGER CHECK (is_plummet IN (0, 1)) DEFAULT 0",
        "is_pre_st": "INTEGER CHECK (is_pre_st IN (0, 1)) DEFAULT 0",
        "is_small_high_open": "INTEGER CHECK (is_small_high_open IN (0, 1)) DEFAULT 0",
        "is_up_broken": "INTEGER CHECK (is_up_broken IN (0, 1)) DEFAULT 0",
        "is_weak": "INTEGER CHECK (is_weak IN (0, 1)) DEFAULT 0",
        "first_limit_up_days": "INTEGER DEFAULT 0",
        "jsjl": "REAL DEFAULT 0.0",
        "cjs": "REAL DEFAULT 0.0",
        "xcjw": "REAL DEFAULT 0.0",
        "jssb": "REAL DEFAULT 0.0",
        "open_pct_rate": "REAL DEFAULT -100.0",
        "open_price": "REAL DEFAULT -1",
        "close_price": "REAL DEFAULT -1",
        "pre_close_price": "REAL DEFAULT -1",
        "next_day_open_price": "REAL DEFAULT -1",
        "next_day_close_price": "REAL DEFAULT -1",
        "next_day_high_price_open_10mins": "REAL DEFAULT -1",
        "next_day_low_price_open_10mins": "REAL DEFAULT -1",
        "next_day_high_price": "REAL DEFAULT -1",
        "next_day_low_price": "REAL DEFAULT -1",
        "in_premarket": "INTEGER CHECK (in_premarket IN (0, 1)) DEFAULT 0",
        "in_premarket_match": "INTEGER CHECK (in_premarket_match IN (0, 1)) DEFAULT 0",
        "mod_code": "TEXT DEFAULT ''",
        "mod_name": "TEXT DEFAULT ''",
        "mod_short_line_score": "REAL DEFAULT -100",
        "mod_short_line_score_change": "REAL DEFAULT -100",
        "mod_short_line_rank": "INTEGER DEFAULT -1",
        "mod_trend_score": "REAL DEFAULT -100",
        "mod_trend_score_change": "REAL DEFAULT -100",
        "mod_trend_rank": "INTEGER DEFAULT -1",
        "env_json_info": "TEXT DEFAULT ''",
        "block_category_info": "TEXT DEFAULT ''",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        #新增字段
        "xcjwV2": "REAL DEFAULT 0.0",
        "jssbV2": "REAL DEFAULT 0.0",
        "cjsV2": "REAL DEFAULT 0.0",
        "isStrengthHigh": "INTEGER CHECK (isStrengthHigh IN (0, 1)) DEFAULT 0",
        "isStrengthMiddle": "INTEGER CHECK (isStrengthMiddle IN (0, 1)) DEFAULT 0",
        "isStrengthLow": "INTEGER CHECK (isStrengthLow IN (0, 1)) DEFAULT 0",
        "isStrengthIncrease": "INTEGER CHECK (isStrengthIncrease IN (0, 1)) DEFAULT 0",
        "isStrengthReduct": "INTEGER CHECK (isStrengthReduct IN (0, 1)) DEFAULT 0",
        "shortLineScore": "REAL DEFAULT 0.0",
        "shortLineScoreChange": "REAL DEFAULT 0.0",
        "jsjlBlock": "REAL DEFAULT 0.0",
        "jssbBlock": "REAL DEFAULT 0.0",
        "cjsBlock": "REAL DEFAULT 0.0",
        "directionCjsV2": "REAL DEFAULT 0.0",
        "circulationMarketValue": "REAL DEFAULT 0.0",
        "cgyk": "TEXT DEFAULT ''",
        "htyk": "TEXT DEFAULT ''",
        "cgykValue": "REAL DEFAULT 0.0",
        "htykValue": "REAL DEFAULT 0.0",
        "isMiddleHighOpen": "INTEGER CHECK (isMiddleHighOpen IN (0, 1)) DEFAULT 0",
        "isLargeHighOpen": "INTEGER CHECK (isLargeHighOpen IN (0, 1)) DEFAULT 0",
        "isSmallLowOpen": "INTEGER CHECK (isSmallLowOpen IN (0, 1)) DEFAULT 0",
        "isMiddleLowOpen": "INTEGER CHECK (isMiddleLowOpen IN (0, 1)) DEFAULT 0",
        "isLargeLowOpen": "INTEGER CHECK (isLargeLowOpen IN (0, 1)) DEFAULT 0",
    }
    with SQLiteManager(db_name) as manager:
        manager.create_table(table_name, columns)

create_premarket_table = partial(create_strategy_table, prefix="strategy_data_premarket_")
create_aftermarket_table = partial(create_strategy_table, prefix="strategy_data_aftermarket_")

# 示例数据
insert_dict = {
    "date_key": "20250209",
    "strategy_name": "SampleStrategy",
    "sub_strategy_name": "SubSample",
    "stock_code": "600001",
    "stock_name": "SampleStock",
    # 可以根据需要添加更多字段
}

delete_dict = {
    "date_key": "20250209",
    "strategy_name": "SampleStrategy"
}

update_dict = {
    "stock_name": "UpdatedStockName"
}

condition_dict = {
    "stock_name": "UpdatedStockName"
}


if __name__ == "__main__":
    with SQLiteManager(db_name) as manager:
       manager.query_limit_up_records_by_date('2025-06-08')

    # with SQLiteManager(db_name) as manager:
    #    manager.update_data("strategy_data_premarket_202503", update_dict, condition_dict)
    # with SQLiteManager(db_name) as manager:
    #    manager.delete_data("strategy_data_premarket_202503", delete_dict)