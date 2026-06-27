from curses import error
import os

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()

class DatabaseConnection:
    def __init__(self):
        self.host = "royalpms-yugdalal97-dd0s.l.aivencloud.com"
        self.username = "avnadmin"
        self.password = os.getenv("DB_PASSWORD")
        self.db_name = "royalpms_cryst8000"
        self.port = 22285

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.username,
                passwd=self.password,
                database=self.db_name,
                port=22285
            )
            print("Connection to MySQL DB successful")
        except Error as e:
            print(f"The error '{e}' occurred")

    def get_database_schema(self):
        try:
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
        except Error as e:
            print(f"The error '{e}' occurred")
            return {error: str(e)}
    
    def get_table_columns(self, table_name):
        try: 
            if not self.connection:
                raise RuntimeError("Database connection is not established")

            cursor = self.connection.cursor()
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            return [{"name": col[0], "type": col[1]} for col in columns]
        except Error as e:
            print(f"The error '{e}' occurred")
            return {error: str(e)}

    def fetch_table_data(self, table_name, filters=None):
        try:
            if not self.connection:
                raise RuntimeError("Database connection is not established")

            cursor = self.connection.cursor(dictionary=True)
            query = f"SELECT * FROM {table_name}"
            
            if filters:
                filter_clauses = [f"{col} LIKE %s" for col in filters.keys()]
                query += " WHERE " + " AND ".join(filter_clauses)
                print("Executing query:", query)
                print("With filters:", filters)
                print("With filter values:", tuple(filters.values()))
                cursor.execute(query, tuple(filters.values()))
            else:
                cursor.execute(query)

            return cursor.fetchall()
        except Error as e:
            print(f"The error '{e}' occurred")
            return {error: str(e)}
    
    def insert_into_table(self,table_name,data:dict):
        try:
            if not self.connection:
                raise RuntimeError("Database connection is not established")
            cursor = self.connection.cursor()
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            print("Executing query:", query)
            cursor.execute(query, tuple(data.values()))
            self.connection.commit()
            print(f"Data inserted into {table_name} successfully.")
            return cursor.lastrowid
        except Error as e:  
            print(f"The error '{e}' occurred")
            return {error: str(e)}
        ``