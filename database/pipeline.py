import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Create database connection
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="giftedgown",
        user="postgres", 
        #create a .env file and add password as DB_PASSWORD=whatever your password is
        password=os.getenv("DB_PASSWORD")
    )
    conn.autocommit = True
    return conn

def get_all_appointments():
    """Retrieve all appointments ordered by date/time"""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM appointments ORDER BY appointment_time DESC"
    cursor.execute(query)
    appointments = cursor.fetchall()
    cursor.close()
    conn.close()
    return appointments

# Angela's queries, in case we need them later
#def get_appointments_by_event_type(): 
# query = "SELECT * FROM appointments WHERE event_type = "
# cursor.execute(query, (event_type,))
#  return cursor.fetchall()

#def search_appointments_by_name(full_name):
#  query = "SELECT * FROM appointments WHERE full_name = "
#  cursor.execute(query, ())
#  return cursor.fetchall()