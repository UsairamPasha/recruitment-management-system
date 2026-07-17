import sqlite3

DATABASE = "database.db"

def get_db():
    """
    Returns a database connection.
    Use this function instead of sqlite3.connect directly.
    """
    conn = sqlite3.connect(DATABASE)
    # Enable returning rows as dictionaries
    conn.row_factory = sqlite3.Row
    return conn
