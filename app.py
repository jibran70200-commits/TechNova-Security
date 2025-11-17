import streamlit as st
import socket
import threading
import time
from collections import defaultdict, deque

# ---------------------------------------------------------
#  CONFIG
# ---------------------------------------------------------
HOST = "127.0.0.1"
PORT = 9999

USERS = {"alice": "alicepass"}

REQUEST_WINDOW = 5
REQUEST_THRESHOLD = 20
BLOCK_DURATION = 20

ip_timestamps = defaultdict(lambda: deque())
blocked_until = {}
connection_counts = defaultdict(int)

lock = threading.Lock()
server_running = False

# ---------------------------------------------------------
#  SERVER LOGIC
# ---------------------------------------------------------
def is_blocked(ip):
    until = blocked_until.get(ip)
    return until and time.time() < until

def register_request(ip):
    now = time.time()
    dq = ip_timestamps[ip]
    dq.append(now)
    while dq and dq[0] < now - REQUEST_WINDOW:
        dq.popleft()
    return len(dq)

def handle_client(conn, addr):
    ip = addr[0]
    with lock:
        connection_counts[ip] += 1

    try:
        data = conn.recv(1024).decode().strip()

        if is_blocked(ip):
            conn.sendall(b"ERROR: IP BLOCKED.\n")
            return

        if not data:
            return

        count = register_request(ip)

        if count > REQUEST_THRESHOLD:
            with lock:
                blocked_until[ip] = time.time() + BLOCK_DURATION
            conn.sendall(b"ALERT: DOS DETECTED. IP BLOCKED.\n")
            return

        parts = data.split()
        if parts[0].upper() == "LOGIN" and len(parts) >= 3:
            user, pwd = parts[1], parts[2]
            if USERS.get(user) == pwd:
                conn.sendall(b"OK: Login successful.\n")
            else:
                conn.sendall(b"ERROR: Incorrect credentials.\n")

        elif parts[0].upper() == "PING":
            conn.sendall(b"PONG\n")
        else:
            conn.sendall(b"OK: Command received.\n")

    except:
        pass
    finally:
        with lock:
            connection_counts[ip] -= 1
        conn.close()

def start_server():
    global server_running
    server_running = True

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(200)

    while server_running:
        try:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except:
            break

    s.close()

def stop_server():
    global server_running
    server_running = False

# ---------------------------------------------------------
#  USER SIMULATION
# ---------------------------------------------------------
def legit_user():
    logs = []

    def send(msg):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(msg.encode() + b"\n")
            return s.recv(1024).decode()

    logs.append(send("LOGIN alice alicepass"))

    for i in range(5):
        logs.append("PING → " + send("PING"))
        time.sleep(1)

    return logs

# ---------------------------------------------------------
#  ATTACKER SIMULATION
# ---------------------------------------------------------
def attacker(flood=200):
    logs = []
    for _ in range(flood):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.sendall(b"FAKECMD attack\n")
                try:
                    logs.append(s.recv(1024).decode())
                except:
                    logs.append("Blocked")
        except:
            logs.append("Connection refused")
    return logs

# ---------------------------------------------------------
#  STREAMLIT UI
# ---------------------------------------------------------
st.title("🔐 Security System Simulation")
st.write("Simple server + DOS simulation (single-file build-friendly version).")

col1, col2 = st.columns(2)

with col1:
    if st.button("▶ Start Server"):
        threading.Thread(target=start_server, daemon=True).start()
        st.success("Server started!")

    if st.button("⛔ Stop Server"):
        stop_server()
        st.error("Server stopped.")

with col2:
    if st.button("👤 Legit User"):
        out = legit_user()
        st.code("\n".join(out))

    if st.button("⚠ Run Attacker Flood"):
        out = attacker()
        st.code("\n".join(out))

st.subheader("📊 Server Status")

with lock:
    st.write("Active Connections:", sum(connection_counts.values()))

    blocked = {
        ip: int(blocked_until[ip] - time.time())
        for ip in blocked_until if blocked_until[ip] > time.time()
    }

    st.write("Blocked IPs:", blocked if blocked else "None")
