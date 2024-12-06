from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit
import os
import uuid
import eventlet

# Patch for Windows compatibility (WebSockets)
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Initialize SocketIO
socketio = SocketIO(app, async_mode='eventlet')

# Store active users in a dictionary (username -> socket_id)
active_users = {}

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Main page to input the username (GET and POST)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the username from the form
        username = request.form['username']
        
        # Redirect to the chat page (passing the username)
        return redirect(url_for('chat', username=username))
    
    # For GET request, render the index page
    return render_template('index.html')

# Chat page, user redirected here after entering the username
@app.route('/chat/<username>')
def chat(username):
    return render_template('chat.html', username=username)

# Event for a new user joining
@socketio.on('set_username')
def set_username(data):
    username = data['username']
    active_users[username] = request.sid  # Store the user's socket ID
    emit('user_list', list(active_users.keys()), broadcast=True)

# Event to handle incoming messages
@socketio.on('message')
def handle_message(data):
    message = data['message']
    sender = data['sender']
    emit('message', {'sender': sender, 'message': message}, broadcast=True)

# Event for file uploads
@socketio.on('file_upload')
def handle_file_upload(data):
    # Assuming data['file'] contains the Base64 encoded file data
    file_data = data['file']['data']
    file_type = data['file']['type']
    filename = str(uuid.uuid4()) + '.' + file_type
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Write the file to the disk
    with open(file_path, 'wb') as f:
        f.write(file_data.decode('base64'))  # Decode from Base64
    
    file_url = f'/uploads/{filename}'  # URL to access the uploaded file
    emit('file_uploaded', {'filename': filename, 'url': file_url}, broadcast=True)

# Disconnecting a user
@socketio.on('disconnect')
def handle_disconnect():
    for username, sid in list(active_users.items()):
        if sid == request.sid:
            del active_users[username]
            emit('user_list', list(active_users.keys()), broadcast=True)
            break

# Run the app and make it accessible on your local network
if __name__ == '__main__':
    # Change '0.0.0.0' to allow access from other devices on the network.
    # Change port if needed (5000 is the default).
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
