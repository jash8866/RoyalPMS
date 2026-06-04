import mysql.connector
from mysql.connector import Error

def create_connection(host, username, password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host,
            user=username,
            passwd=password,
            database=db_name
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection