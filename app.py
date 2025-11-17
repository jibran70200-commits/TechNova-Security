import streamlit as st
import socket
import threading
import time
from collections import defaultdict, deque
from pyvis.network import Network
import tempfile
import os

# ---------------------------------------------------------
#  CONFIG
# ---------------------------------------------------------
HOST = "127.0.0.1"
PORT = 9999

USERS = {"alice": "alicepass"}  # simple user db

REQUEST_WINDOW = 5          # seconds
REQUEST_THRESHOLD = 20      # request limit
BLOCK_DURATION = 20         # seconds

ip_timestamps = defaultdict(lambda: deque())
blocked_until = {}
connection_counts = defaultdict(int)

lock = threading.Lock()

# Server state
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
        if is_blocked(ip):
            conn.sendall(b"ERROR: IP BLOCKED.\n")
            return

        data = conn.recv(1024).decode().strip()
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
        try:
            conn.close()
        except:
            pass

        with lock:
            connection_counts[ip] -= 1

def monitor_thread():
    while server_running:
        time.sleep(2)

def start_server():
    global server_running
    server_running = True

    threading.Thread(target=monitor_thread, daemon=True).start()

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
    def send(msg):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(msg.encode() + b"\n")
            return s.recv(1024).decode()

    logs = []
    logs.append(send("LOGIN alice alicepass"))
    for i in range(5):
        logs.append(f"PING {i+1} → " + send("PING"))
        time.sleep(1)
    return logs

# ---------------------------------------------------------
#  ATTACKER SIMULATION
# ---------------------------------------------------------
def attacker(flood_count=200):
    logs = []
    for i in range(flood_count):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.sendall(b"FAKECMD attack\n")
                try:
                    resp = s.recv(1024).decode()
                    logs.append(resp)
                except:
                    pass
        except:
            logs.append("Connection refused / blocked")
    return logs

# ---------------------------------------------------------
#  LIVE NETWORK GRAPH
# ---------------------------------------------------------
def generate_graph():
    net = Network(height="500px", width="100%", bgcolor="#000000", font_color="white")

    net.add_node("SERVER", color="red", size=30)

    # clients as nodes
    for ip in ip_timestamps.keys():
        count = len(ip_timestamps[ip])
        color = "orange"
        size = 15 + min(count, 30)

        if is_blocked(ip):
            color = "red"

        net.add_node(ip, color=color, size=size)
        net.add_edge(ip, "SERVER")

    temp_path = tempfile.gettempdir() + "/network_graph.html"
    net.save_graph(temp_path)
    return temp_path

# ---------------------------------------------------------
#  STREAMLIT UI
# ---------------------------------------------------------
st.title("🔐 Security System Simulation — Streamlit")
st.write("Single-file simulation: Server + Legit User + Attacker + Live Graph")

col1, col2 = st.columns(2)

with col1:
    if st.button("▶ Start Server"):
        threading.Thread(target=start_server, daemon=True).start()
        st.success("Server started!")

    if st.button("⛔ Stop Server"):
        stop_server()
        st.error("Server stopped.")

with col2:
    if st.button("👤 Run Legit User"):
        out = legit_user()
        st.code("\n".join(out))

    if st.button("⚠ Run Attacker (Flood)"):
        out = attacker(200)
        st.code("\n".join(out))

st.subheader("📡 Live Network Graph")
if st.button("Generate Graph"):
    path = generate_graph()
    st.success("Graph generated below 👇")
    html = open(path, "r", encoding="utf-8").read()
    st.components.v1.html(html, height=500, scrolling=True)

st.subheader("📊 Server Status")

with lock:
    st.write("Active Connections:", sum(connection_counts.values()))
    st.write("Blocked IPs:", 
             {ip: int(blocked_until[ip]-time.time()) 
              for ip in blocked_until if blocked_until[ip] > time.time()})
