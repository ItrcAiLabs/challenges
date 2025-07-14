import psycopg2

conn = psycopg2.connect( dbname='evalai', user='postgres', password='postgres', host='localhost', port='5432' )

cur = conn.cursor()

cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
tables = cur.fetchall()

for table in tables:
	print (f"TRUNCATE TABLE {table[0]} CASCADE;")

cur.close()
conn.close()
