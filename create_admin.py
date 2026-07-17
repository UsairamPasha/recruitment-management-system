from werkzeug.security import generate_password_hash
import sqlite3

def create_admin(first_name="Admin", last_name="User", username="admin", email="admin@example.com", password="admin123"):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    hashed_password = generate_password_hash(password)

    try:
        cursor.execute("""
            INSERT INTO users (first_name, last_name, username, email, password, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, username, email, hashed_password, "admin"))
        conn.commit()
        print("Admin user created successfully!")
    except Exception:
        print("Admin already exists or error occurred")
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin()
