import os
import sqlite3
from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

# 🔥 IMPORTANT FIX: Increase Socket.IO payload limit
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    max_http_buffer_size=100 * 1024 * 1024  # 100MB
)

DB = "chat.db"
online_users = {}

# ---------------- DATABASE ----------------
def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
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

# ---------------- ROUTE ----------------
@app.route('/')
def index():
    return render_template('index.html')

# ---------------- SOCKET EVENTS ----------------
@socketio.on('join_room')
def join(data):
    username = data['username']
    room = data['room']

    join_room(room)

    online_users.setdefault(room, set()).add(username)
    emit('update_users', list(online_users[room]), to=room)

    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT username, message, image FROM messages WHERE room=?",
            (room,)
        ).fetchall()

    for r in rows:
        emit('receive_history', {
            "username": r[0],
            "message": r[1],
            "image": r[2]
        })

@socketio.on('room_message')
def handle_message(data):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO messages (room, username, message) VALUES (?, ?, ?)",
            (data['room'], data['username'], data['msg'])
        )
        con.commit()

    emit('receive_message', data, to=data['room'])

@socketio.on('image_upload')
def image_upload(data):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO messages (room, username, image) VALUES (?, ?, ?)",
            (data['room'], data['username'], data['file'])
        )
        con.commit()

    emit('image_message', {
        "username": data['username'],
        "image_url": data['file']
    }, to=data['room'])

@socketio.on('typing')
def typing(data):
    emit('show_typing', data['username'], to=data['room'], include_self=False)

@socketio.on('stop_typing')
def stop_typing(data):
    emit('hide_typing', to=data['room'], include_self=False)

@socketio.on('disconnect')
def disconnect():
    for room in online_users:
        online_users[room].clear()

# ---------------- RUN ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)

