import mysql.connector
from mysql.connector import Error

class DatabaseConnection:
    def __init__(self):
        self.host = "localhost"
        self.username = "root"
        self.password = ""
        self.db_name = "royalpms_cryst8000"
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

    def fetch_table_data(self, table_name, filters=None):
        if not self.connection:
            raise RuntimeError("Database connection is not established")

        cursor = self.connection.cursor(dictionary=True)
        query = f"SELECT * FROM {table_name}"
        
        if filters:
            filter_clauses = [f"{col} = %s" for col in filters.keys()]
            query += " WHERE " + " AND ".join(filter_clauses)
            cursor.execute(query, tuple(filters.values()))
        else:
            cursor.execute(query)

        return cursor.fetchall()