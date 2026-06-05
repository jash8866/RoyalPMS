import mysql.connector
from mysql.connector import Error

class DatabaseConnection:
    def __init__(self, host, username, password, db_name):
        self.host = host
        self.username = username
        self.password = password
        self.db_name = db_name
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.username,
                passwd=self.password,
                database=self.db_name
            )
            print("Connection to MySQL DB successful")
        except Error as e:
            print(f"The error '{e}' occurred")

    def get_database_schema(self):
        if not self.connection:
            raise RuntimeError("Database connection is not established")

        cursor = self.connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        schema = {}
        for (table_name,) in tables:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            schema[table_name] = [{"name": col[0], "type": col[1]} for col in columns]

        return schema

    def fetch_reservations(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM reservations")
        return cursor.fetchall()
    
    def fetch_guests(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM guests")
        return cursor.fetchall()