import os
import sqlite3
from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

socketio = SocketIO(app, cors_allowed_origins="*")

DB_NAME = "chat.db"

# ---------- DATABASE ----------
def init_db():
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT,
            username TEXT,
            message TEXT,
            image TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        con.commit()

init_db()

# ---------- ROUTE ----------
@app.route('/')
def index():
    return render_template('index.html')

# ---------- SOCKET EVENTS ----------
@socketio.on('join_room')
def join(data):
    room = data['room']
    join_room(room)

    # Send previous messages
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute("SELECT username, message, image FROM messages WHERE room=?", (room,))
        history = cur.fetchall()

    for msg in history:
        emit('receive_history', {
            "username": msg[0],
            "message": msg[1],
            "image": msg[2]
        })

    emit('status', f"🟢 {data['username']} joined", to=room)

@socketio.on('send_message')
def message(data):
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO messages (room, username, message) VALUES (?, ?, ?)",
            (data['room'], data['username'], data['message'])
        )
        con.commit()

    emit('receive_message', data, to=data['room'])

@socketio.on('send_image')
def image(data):
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO messages (room, username, image) VALUES (?, ?, ?)",
            (data['room'], data['username'], data['image'])
        )
        con.commit()

    emit('receive_image', data, to=data['room'])

@socketio.on('typing')
def typing(data):
    emit('typing', data, to=data['room'], include_self=False)

# ---------- RUN ----------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
