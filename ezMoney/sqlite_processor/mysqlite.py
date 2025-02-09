import sqlite3
from datetime import datetime

db_name = r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db'


class SQLiteManager:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
    
    def create_table(self, table_name, columns):
        column_definitions = ', '.join([f"{col} {col_type}" for col, col_type in columns.items()])
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions})"
        self.cursor.execute(create_table_query)


    def insert_data(self, table_name, data_dict):
        columns = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?' for _ in data_dict])
        values = tuple(data_dict.values())
        insert_query = f"INSERT INTO strategy_data_premarket_202502 ({columns}) VALUES ({placeholders})"
        cursor.execute(insert_query, values)
        conn.commit()
        print("Data inserted successfully.")
    
    def close(self):
        self.conn.close()
        

def create_table():
    # 获取当前日期
    current_date = datetime.now().strftime("%Y%m")
    # 表名
    table_name = f"strategy_data_premarket_{current_date}"
    # 连接到SQLite数据库
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # SQL创建表的语句
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_key TEXT NOT NULL,
        strategy_name TEXT NOT NULL,
        sub_strategy_name TEXT DEFAULT '',
        stock_code TEXT NOT NULL,
        stock_name TEXT DEFAULT '',
        block_category TEXT DEFAULT '',
        block_codes TEXT DEFAULT '',
        industry_code TEXT DEFAULT '',
        max_block_category_rank INTEGER DEFAULT -1,
        max_block_code_rank INTEGER DEFAULT -1,
        max_industry_code_rank INTEGER DEFAULT -1,
        is_bottom INTEGER CHECK (is_bottom IN (0, 1)) DEFAULT 0,
        is_broken_plate INTEGER CHECK (is_broken_plate IN (0, 1)) DEFAULT 0,
        is_down_broken INTEGER CHECK (is_down_broken IN (0, 1)) DEFAULT 0,
        is_fall INTEGER CHECK (is_fall IN (0, 1)) DEFAULT 0,
        is_first_down_broken INTEGER CHECK (is_first_down_broken IN (0, 1)) DEFAULT 0,
        is_first_up_broken INTEGER CHECK (is_first_up_broken IN (0, 1)) DEFAULT 0,
        is_gestation_line INTEGER CHECK (is_gestation_line IN (0, 1)) DEFAULT 0,
        is_half INTEGER CHECK (is_half IN (0, 1)) DEFAULT 0,
        is_high INTEGER CHECK (is_high IN (0, 1)) DEFAULT 0,
        is_highest INTEGER CHECK (is_highest IN (0, 1)) DEFAULT 0,
        is_long_shadow INTEGER CHECK (is_long_shadow IN (0, 1)) DEFAULT 0,
        is_low INTEGER CHECK (is_low IN (0, 1)) DEFAULT 0,
        is_medium INTEGER CHECK (is_medium IN (0, 1)) DEFAULT 0,
        is_meso INTEGER CHECK (is_meso IN (0, 1)) DEFAULT 0,
        is_plummet INTEGER CHECK (is_plummet IN (0, 1)) DEFAULT 0,
        is_pre_st INTEGER CHECK (is_pre_st IN (0, 1)) DEFAULT 0,
        is_small_high_open INTEGER CHECK (is_small_high_open IN (0, 1)) DEFAULT 0,
        is_up_broken INTEGER CHECK (is_up_broken IN (0, 1)) DEFAULT 0,
        is_weak INTEGER CHECK (is_weak IN (0, 1)) DEFAULT 0,
        first_limit_up_days INTEGER DEFAULT 0,
        jsjl REAL DEFAULT 0.0,
        cjs REAL DEFAULT 0.0,
        xcjw REAL DEFAULT 0.0,
        jssb REAL DEFAULT 0.0,
        open_pct_rate REAL DEFAULT -100.0,
        open_price REAL DEFAULT -1,
        close_price REAL DEFAULT -1,
        pre_close_price REAL DEFAULT -1,
        next_day_open_price REAL DEFAULT -1,
        next_day_close_price REAL DEFAULT -1,
        next_day_high_price_open_10mins REAL DEFAULT -1,
        next_day_low_price_open_10mins REAL DEFAULT -1,
        next_day_high_price REAL DEFAULT -1,
        next_day_low_price REAL DEFAULT -1,
        in_premarket INTEGER CHECK (in_premarket IN (0, 1)) DEFAULT 0,
        in_premarket_match INTEGER CHECK (in_premarket_match IN (0, 1)) DEFAULT 0,
        mod_code TEXT DEFAULT '',
        mod_name TEXT DEFAULT '',
        mod_short_line_score REAL DEFAULT -100,
        mod_short_line_score_change REAL DEFAULT -100,
        mod_short_line_rank INTEGER DEFAULT -1,
        mod_trend_score REAL DEFAULT -100,
        mod_trend_score_change REAL DEFAULT -100,
        mod_trend_rank INTEGER DEFAULT -1,
        env_json_info TEXT DEFAULT '',
        block_category_info TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (date_key, strategy_name, sub_strategy_name, stock_code)
    )
    """

    # 执行创建表的语句
    cursor.execute(create_table_query)

    # 提交更改并关闭连接
    conn.commit()
    conn.close()


# 连接到 SQLite 数据库
conn = sqlite3.connect('your_database.db')
cursor = conn.cursor()

# 插入数据
def insert_data(data_dict):
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join(['?' for _ in data_dict])
    values = tuple(data_dict.values())
    insert_query = f"INSERT INTO strategy_data_premarket_202502 ({columns}) VALUES ({placeholders})"
    cursor.execute(insert_query, values)
    conn.commit()
    print("Data inserted successfully.")

# 删除数据
def delete_data(condition_dict):
    conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
    values = tuple(condition_dict.values())
    delete_query = f"DELETE FROM strategy_data_premarket_202502 WHERE {conditions}"
    cursor.execute(delete_query, values)
    conn.commit()
    print("Data deleted successfully.")

# 更新数据
def update_data(update_dict, condition_dict):
    set_clause = ', '.join([f"{key} = ?" for key in update_dict])
    conditions = ' AND '.join([f"{key} = ?" for key in condition_dict])
    values = tuple(update_dict.values()) + tuple(condition_dict.values())
    update_query = f"UPDATE strategy_data_premarket_202502 SET {set_clause} WHERE {conditions}"
    cursor.execute(update_query, values)
    conn.commit()
    print("Data updated successfully.")

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
    "date_key": "20250209",
    "strategy_name": "SampleStrategy"
}

# 执行插入操作
insert_data(insert_dict)

# 执行删除操作
delete_data(delete_dict)

# 执行更新操作
update_data(update_dict, condition_dict)

# 关闭数据库连接
conn.close()



if __name__ == "__main__":
    create_table()


    
