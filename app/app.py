from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, send, emit
import redis
import os

app = Flask(__name__)
app.secret_key = "secret123"

# Redis connection (LOCAL)
redis_url = os.getenv("REDIS_URL", "redis://host.docker.internal:6379/0")
r = redis.Redis.from_url(redis_url)

# SocketIO (threading mode)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# ---------------- ROUTES ----------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")

        if username:
            session["user"] = username
            return redirect("/chat")

    return render_template("login.html")


@app.route("/chat")
def chat():
    if "user" not in session:
        return redirect("/")
    return render_template("chat.html", user=session["user"])


# ---------------- SOCKET EVENTS ----------------

# Send message
@socketio.on("message")
def handle_message(msg):
    user = session.get("user", "Anonymous")
    full_msg = f"{user}: {msg}"

    # Publish to Redis
    r.publish("chat", full_msg)

    # Send to all clients
    send(full_msg, broadcast=True)


# Typing indicator
@socketio.on("typing")
def typing(user):
    emit("typing", user, broadcast=True, include_self=False)


# ---------------- REDIS LISTENER ----------------

def redis_listener():
    pubsub = r.pubsub()
    pubsub.subscribe("chat")

    for message in pubsub.listen():
        if message["type"] == "message":
            socketio.send(message["data"].decode())


# ---------------- MAIN ----------------

if __name__ == "__main__":
    socketio.start_background_task(redis_listener)

    socketio.run(app, host="0.0.0.0", port=5001, allow_unsafe_werkzeug=True)