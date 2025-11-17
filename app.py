import socket
import threading
import time
from collections import defaultdict, deque

HOST = "127.0.0.1"
PORT = 9999

USERS = {"alice": "alicepass"}

# DOS settings
REQUEST_WINDOW = 5
REQUEST_THRESHOLD = 20
BLOCK_DURATION = 20

ip_timestamps = defaultdict(lambda: deque())
blocked_until = {}
connection_counts = defaultdict(int)

lock = threading.Lock()
server_running = False

# -----------------------------------------------------
# SERVER CODE
# -----------------------------------------------------

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
        if not data:
            return

        # Check if IP is blocked
        if is_blocked(ip):
            conn.sendall(b"ERROR: Your IP is BLOCKED\n")
            return

        # DOS check
        count = register_request(ip)
        if count > REQUEST_THRESHOLD:
            with lock:
                blocked_until[ip] = time.time() + BLOCK_DURATION
            conn.sendall(b"ALERT: DOS detected → IP BLOCKED\n")
            print(f"[BLOCKED] {ip} banned for {BLOCK_DURATION} sec")
            return

        parts = data.split()

        # LOGIN user pass
        if parts[0].upper() == "LOGIN" and len(parts) >= 3:
            user = parts[1]
            pwd = parts[2]
            if USERS.get(user) == pwd:
                conn.sendall(b"OK: Login successful\n")
            else:
                conn.sendall(b"ERROR: Wrong credentials\n")

        elif parts[0].upper() == "PING":
            conn.sendall(b"PONG\n")

        else:
            conn.sendall(b"OK: Command received\n")

    except Exception as e:
        print("Client error:", e)

    finally:
        try:
            conn.close()
        except:
            pass

        with lock:
            connection_counts[ip] -= 1


def start_server():
    global server_running
    server_running = True

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(200)

    print(f"\n[SERVER STARTED] Listening on {HOST}:{PORT}\n")

    try:
        while server_running:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except:
        pass
    finally:
        s.close()
        print("\n[SERVER STOPPED]\n")


# -----------------------------------------------------
# USER CLIENT
# -----------------------------------------------------

def legit_user():
    print("\n[USER] Connecting...\n")

    def send(msg):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.sendall(msg.encode() + b"\n")
        data = s.recv(1024).decode()
        s.close()
        return data

    print(send("LOGIN alice alicepass"))

    for i in range(5):
        print("PING →", send("PING"))
        time.sleep(1)


# -----------------------------------------------------
# ATTACKER CLIENT
# -----------------------------------------------------

def attacker():
    print("\n[ATTACKER STARTED] Flooding server...\n")

    ip = "attacker"

    for i in range(300):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            s.sendall(b"FAKECMD attack\n")
            try:
                print(s.recv(1024).decode().strip())
            except:
                pass
            s.close()
        except:
            print("Connection refused / blocked")
        time.sleep(0.01)

    print("\n[ATTACKER FINISHED]\n")


# -----------------------------------------------------
# MENU
# -----------------------------------------------------

def menu():
    print("""
===============================
   SECURITY SYSTEM SIMULATOR
===============================
1. Start Server
2. Run Legit User
3. Run Attacker (DOS)
4. Exit
""")

    choice = input("Enter choice: ")

    if choice == "1":
        threading.Thread(target=start_server, daemon=True).start()
        menu()

    elif choice == "2":
        legit_user()
        menu()

    elif choice == "3":
        attacker()
        menu()

    elif choice == "4":
        print("Exiting...")
        exit()

    else:
        print("Invalid choice")
        menu()


if __name__ == "__main__":
    menu()
