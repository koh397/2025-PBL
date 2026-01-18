import MySQLdb

con = MySQLdb.connect(
    host = "localhost",
    user = "root",
    passwd = "chiffon0301",
    db = "健康管理")
cur = con.cursor()

cur.execute("ALTER TABLE list ADD COLUMN target_weight DOUBLE DEFAULT 0;")
con.commit()
con.close()
print("Database updated successfully.")