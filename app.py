import os
import base64
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

socketio = SocketIO(app, cors_allowed_origins="*")

# Track users per room
users_in_rooms = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room = data['room']

    join_room(room)

    if room not in users_in_rooms:
        users_in_rooms[room] = []

    if username not in users_in_rooms[room]:
        users_in_rooms[room].append(username)

    emit('update_users', users_in_rooms[room], to=room)
    emit('message', f"{username} joined the room", to=room)


@socketio.on('room_message')
def handle_message(data):
    emit('message', data['msg'], to=data['room'])


@socketio.on('typing')
def handle_typing(data):
    emit('show_typing', data['username'], to=data['room'], include_self=False)


@socketio.on('stop_typing')
def handle_stop_typing(data):
    emit('hide_typing', data['username'], to=data['room'], include_self=False)


@socketio.on('image_upload')
def handle_image(data):
    filename = secure_filename(data['filename'])

    if not allowed_file(filename):
        return

    image_data = base64.b64decode(data['file'].split(',')[1])
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    with open(filepath, 'wb') as f:
        f.write(image_data)

    emit('image_message', {
        'username': data['username'],
        'image_url': f"/static/uploads/{filename}"
    }, to=data['room'])


@socketio.on('disconnect')
def handle_disconnect():
    for room in users_in_rooms:
        emit('update_users', users_in_rooms[room], to=room)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
