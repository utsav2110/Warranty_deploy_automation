import psycopg2
import os

conn = psycopg2.connect(
    host=os.environ["SUPABASE_HOST"],
    dbname=os.environ["SUPABASE_DB"],
    user=os.environ["SUPABASE_USER"],
    password=os.environ["SUPABASE_PASS"],
    port=6543
)

cur = conn.cursor()
cur.execute("DELETE FROM warranty_items WHERE warranty_end_date < CURRENT_DATE;")
conn.commit()
cur.close()
conn.close()

print("✅ Expired items deleted from Supabase")
