import streamlit as st
import time
from collections import defaultdict, deque
import random

st.set_page_config(page_title="Security Simulation", page_icon="🔐")

# ---------------------------------------------------------
# SIMULATED SERVER STATE (No real networking)
# ---------------------------------------------------------
USERS = {"alice": "alicepass"}

REQUEST_WINDOW = 5
REQUEST_THRESHOLD = 20
BLOCK_DURATION = 20

request_log = defaultdict(lambda: deque())
blocked_until = {}
active_connections = defaultdict(int)

# ---------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------
def is_blocked(ip):
    until = blocked_until.get(ip)
    return until and time.time() < until

def register_request(ip):
    now = time.time()
    dq = request_log[ip]
    dq.append(now)
    while dq and dq[0] < now - REQUEST_WINDOW:
        dq.popleft()
    return len(dq)

# ---------------------------------------------------------
# SIMULATED SERVER LOGIC
# ---------------------------------------------------------
def simulated_server_request(ip, command):
    if is_blocked(ip):
        return "❌ IP BLOCKED"

    req_count = register_request(ip)

    if req_count > REQUEST_THRESHOLD:
        blocked_until[ip] = time.time() + BLOCK_DURATION
        return "🚨 DOS DETECTED → IP BLOCKED"

    parts = command.split()

    if parts[0].upper() == "LOGIN":
        if USERS.get(parts[1]) == parts[2]:
            return "✅ Login successful"
        else:
            return "❌ Incorrect credentials"

    if parts[0].upper() == "PING":
        return "🏓 PONG"

    return "✔ Command received"

# ---------------------------------------------------------
# USER SIMULATION
# ---------------------------------------------------------
def legit_user():
    ip = "USER_IP"
    logs = []

    logs.append(simulated_server_request(ip, "LOGIN alice alicepass"))
    for i in range(5):
        logs.append(f"PING {i+1} → " + simulated_server_request(ip, "PING"))
        time.sleep(0.3)

    return logs

# ---------------------------------------------------------
# ATTACKER SIMULATION
# ---------------------------------------------------------
def attacker_sim():
    ip = "ATTACKER_IP"
    logs = []

    for _ in range(200):
        resp = simulated_server_request(ip, "FAKECMD")
        logs.append(resp)

    return logs

# ---------------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------------
st.title("🔐 Security System Simulation (Streamlit Safe Version)")
st.write("This version **does not use sockets**, so it runs correctly on Streamlit Cloud.")

col1, col2 = st.columns(2)

with col1:
    if st.button("👤 Run Legit User"):
        output = legit_user()
        st.code("\n".join(output))

with col2:
    if st.button("⚠ Run DOS Attacker"):
        output = attacker_sim()
        st.code("\n".join(output))

# ---------------------------------------------------------
# Display Server State
# ---------------------------------------------------------
st.subheader("📊 Server Monitoring")

# Active connection count (simulated)
st.write("Active Connections:", random.randint(1, 5))

# Blocked IPs
blocked = {ip: int(blocked_until[ip] - time.time())
           for ip in blocked_until if blocked_until[ip] > time.time()}

st.write("Blocked IPs:", blocked if blocked else "None")

# Request logs
st.subheader("📜 Recent Request Count")

display_counts = {ip: len(request_log[ip]) for ip in request_log}
st.json(display_counts)
