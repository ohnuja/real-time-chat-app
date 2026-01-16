from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

# IMPORTANT: threading mode (Windows safe)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_room')
def handle_join_room(data):
    username = data['username']
    room = data['room']
    join_room(room)
    emit('message', f"{username} has joined the room '{room}'", to=room)

@socketio.on('room_message')
def handle_room_message(data):
    room = data['room']
    msg = data['msg']
    emit('message', msg, to=room)

import os

if __name__ == '__main__':
    # Render provides a PORT environment variable; if it's not there, default to 5000
    port = int(os.environ.get("PORT", 5000))
    
    # Use 0.0.0.0 to allow Render's network to access the app
    socketio.run(app, host='0.0.0.0', port=port)


