from db import get_connection
from models import COMPONENT_TABLE

conn = get_connection()

cursor = conn.cursor()

cursor.execute(COMPONENT_TABLE)

conn.commit()

conn.close()

print("Database Initialized Successfully!")