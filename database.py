import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
# conn = sqlite3.connect("messages.db")
# cursor = conn.cursor()

# Create table to store messages
# query = """
#     CREATE TABLE IF NOT EXISTS messages (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         from_user TEXT NOT NULL,
#         message TEXT NOT NULL
#     )
# """
# cursor.execute(query)
# conn.commit()


def add_message(from_user, message):
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()

    # Create table if not exists (safe to keep here for first-time setup)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user TEXT NOT NULL,
        message TEXT NOT NULL
    )
    ''')

    # Limit to 30 messages
    cursor.execute("SELECT COUNT(*) FROM messages")
    count = cursor.fetchone()[0]

    if count >= 30:
        cursor.execute(
            "DELETE FROM messages WHERE id = (SELECT id FROM messages ORDER BY id ASC LIMIT 1)")

    cursor.execute(
        "INSERT INTO messages (from_user, message) VALUES (?, ?)", (from_user, message))
    conn.commit()
    conn.close()


# def get_all_messages():
#     conn = sqlite3.connect(messages.db)
#     cursor = conn.cursor()
#     cursor.execute("SELECT from_user, message FROM messages ORDER BY id ASC")
#     return cursor.fetchall()


if __name__ == "__main__":
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute("SELECT from_user, message FROM messages ORDER BY id ASC")
    cursor.execute("DELETE FROM messages;")
    conn.commit()
    messages = cursor.fetchall()
    # add_message('test', '1')
    for msg in messages:
        print('msg: ', msg)
    cursor.close()
    conn.close()
