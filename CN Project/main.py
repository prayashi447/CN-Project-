from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__) 
app.config["SECRET_KEY"] = "hjhjsdahhds"  # Set secret key for session management
socketio = SocketIO(app)  # Initialize SocketIO for real-time communication

rooms = {}  # Dictionary to store information about chat rooms
users_in_rooms = {}  # Dictionary to store users in each chat room

# Function to generate a unique room code
def generate_unique_code(length):
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        if code not in rooms:
            break
    return code

# Route for the home page
@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()  # Clear session data
    if request.method == "POST":
        name = request.form.get("name")  # Get user's name from form
        code = request.form.get("code")  # Get room code from form
        join = request.form.get("join", False)  # Check if join button is pressed
        create = request.form.get("create", False)  # Check if create button is pressed
        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            if room in rooms:
                return render_template("home.html", error="Room code already exists. Please choose another.", code=code, name=name)
            room = generate_unique_code(4)  # Generate unique room code
            rooms[room] = {"members": 0, "messages": []}  # Initialize room data
            users_in_rooms[room] = set()  # Initialize user set for the new room
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        if name in users_in_rooms.get(room, set()):
            return render_template("home.html", error="You are already in this chat room.", code=code, name=name)
        
        session["room"] = room  # Store room code in session
        session["name"] = name  # Store user's name in session
        users_in_rooms[room].add(name)  # Add user to the set of users in the room
        return redirect(url_for("room"))  # Redirect to chat room
    return render_template("home.html")  # Render home page template

# Route for the chat room
@app.route("/room")
def room():
    room = session.get("room")  # Get room code from session
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))  # Redirect to home page if session data is missing or room doesn't exist
    
    # Get messages for the room
    messages = rooms.get(room, {}).get("messages", [])

    return render_template("room.html", code=room, messages=messages)  # Pass messages to the template


# Event handler for receiving messages
# Event handler for receiving messages
# Event handler for receiving messages
@socketio.on("message")
def message(data):
    room = session.get("room")  # Get room code from session
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),  # Get user's name from session
        "message": data["data"]  # Get message content from data
    }
    send(content, to=room)  # Send message to all users in the room
    rooms[room]["messages"].append(content)  # Add message to room's message history



# Event handler for user connection
@socketio.on("connect")
def connect(auth):
    room = session.get("room")  # Get room code from session
    name = session.get("name")  # Get user's name from session
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)  
    send({"name": name, "message": "has entered the room"}, to=room)  # Send notification of user's entrance to room
    rooms[room]["members"] += 1  
    print(f"{name} joined room {room}") 

# Event handler for user disconnection
@socketio.on("disconnect")
def disconnect():
    room = session.get("room")  # Get room code from session
    name = session.get("name")  # Get user's name from session
    if room is None or name is None:
        return
    
    leave_room(room)  
    
    # Remove user from the set of users in the room
    users_in_room = users_in_rooms.get(room)
    if users_in_room:
        users_in_room.discard(name)
        if not users_in_room:
            del rooms[room]  # Delete the room if no members are left

    # Send notification of user's departure from room
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")  # Print user's departure to server console

@socketio.on("image")
def image(data):
    room = session.get("room")  # Get room code from session
    if room not in rooms:
        return 
    
    # Ensure that the data contains the image in base64 format
    if "data" in data:
        image_data = data["data"]
        if "," in image_data:
            image_data = image_data.split(",")[1]  # Get base64 encoded image content
    else:
        return
    
    content = {
        "name": session.get("name"),  # Get user's name from session
        "image": image_data  # Store the base64 encoded image content
    }
    send(content, to=room)  # Send image to all users in the room
    rooms[room]["messages"].append(content)  # Add image to room's message history




# Run the application
if __name__ == "__main__":
    socketio.run(app, debug=True, ssl_context=("cert.pem","key.pem"))
