import sqlite3

# 指定工作文件夹和数据库文件名
db_folder = r'D:\workspace\TradeX\sqlite'
db_file = 'example.db'
db_path = f'{db_folder}/{db_file}'

# 连接到指定路径的数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 执行一些操作，例如创建表
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER
)
''')

# 插入数据
cursor.execute("INSERT INTO users (name, age) VALUES (?,?)", ('John Doe', 25))
cursor.execute("INSERT INTO users (name, age) VALUES (?,?)", ('Jane Smith', 30))

# 提交事务
conn.commit()

# 查询数据
cursor.execute("SELECT * FROM users")
rows = cursor.fetchall()
print("所有用户:")
for row in rows:
    print(row)

# 更新数据
cursor.execute("UPDATE users SET age =? WHERE name =?", (26, 'John Doe'))
conn.commit()

# 查询更新后的数据
cursor.execute("SELECT * FROM users WHERE name =?", ('John Doe',))
row = cursor.fetchone()
print("\n更新后的 John Doe:")
print(row)

# 删除数据
cursor.execute("DELETE FROM users WHERE name =?", ('Jane Smith',))
conn.commit()

# 查询删除后的数据
cursor.execute("SELECT * FROM users")
rows = cursor.fetchall()
print("\n删除 Jane Smith 后的所有用户:")
for row in rows:
    print(row)

# 关闭游标和连接
cursor.close()
conn.close()

