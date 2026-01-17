import os
import sqlite3
from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

# Increase limit so images work well
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

socketio = SocketIO(app, cors_allowed_origins="*")

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

    # Track online users
    online_users.setdefault(room, set()).add(username)

    emit('update_users', list(online_users[room]), to=room)

    # Send chat history
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT username, message, image FROM messages WHERE room=?",
            (room,)
        ).fetchall()

    for r in rows:
        if r[1]:
            emit('message', f"{r[0]}: {r[1]}")
        if r[2]:
            emit('image_message', {
                "username": r[0],
                "image_url": r[2]
            })

@socketio.on('room_message')
def handle_message(data):
    room = data['room']
    msg = data['msg']

    username = msg.split(":")[0]

    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO messages (room, username, message) VALUES (?, ?, ?)",
            (room, username, msg.replace(username + ": ", ""))
        )

    emit('message', msg, to=room)

@socketio.on('image_upload')
def image_upload(data):
    room = data['room']
    username = data['username']
    image = data['file']

    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO messages (room, username, image) VALUES (?, ?, ?)",
            (room, username, image)
        )

    emit('image_message', {
        "username": username,
        "image_url": image
    }, to=room)

@socketio.on('typing')
def typing(data):
    emit('show_typing', data['username'], to=data['room'], include_self=False)

@socketio.on('stop_typing')
def stop_typing(data):
    emit('hide_typing', to=data['room'], include_self=False)

@socketio.on('disconnect')
def disconnect():
    # Clean online users (best-effort)
    for room in online_users:
        online_users[room] = set()

# ---------------- RUN ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)


