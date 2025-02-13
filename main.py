import os
import sqlite3
import time
import requests
import threading
import schedule
import json
import logging
from signal import signal, SIGINT
from concurrent.futures import ThreadPoolExecutor
import psutil

# Load configuration from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

_db_address = config['db_address']
_max_allowed_connections = config['max_allowed_connections']
_user_last_id = config.get('user_last_id', 0)
_telegrambot_token = config['telegrambot_token']
_telegram_chat_id = config['telegram_chat_id']
_ignored_users = config.get('ignored_users', [])  # List of user IDs to ignore

# Set up logging
logging.basicConfig(
    filename='xui_monitor.log',
    level=logging.WARNING,  # Reduced logging level
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Graceful shutdown handler
def shutdown_handler(signal_received, frame):
    logging.info("Script terminated gracefully.")
    exit(0)

signal(SIGINT, shutdown_handler)

def getUsers():
    global _user_last_id
    users_list = []
    try:
        conn = sqlite3.connect(_db_address)
        cursor = conn.execute(f"SELECT id, remark, port FROM inbounds WHERE id > {_user_last_id}")
        for c in cursor:
            if c[0] not in _ignored_users:  # Skip ignored users
                users_list.append({'id': c[0], 'name': c[1], 'port': c[2]})
                _user_last_id = c[0]
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in getUsers: {e}")
    return users_list

def disableAccount(user_port):
    try:
        conn = sqlite3.connect(_db_address)
        conn.execute(f"UPDATE inbounds SET enable = 0 WHERE port = {user_port}")
        conn.commit()
        conn.close()
        time.sleep(2)
        os.popen("x-ui restart")
        time.sleep(3)
    except sqlite3.Error as e:
        logging.error(f"Database error in disableAccount: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in disableAccount: {e}")

def checkNewUsers():
    try:
        conn = sqlite3.connect(_db_address)
        cursor = conn.execute(f"SELECT COUNT(*) FROM inbounds WHERE id > {_user_last_id}")
        new_counts = cursor.fetchone()[0]
        conn.close()
        if new_counts > 0:
            init()
    except sqlite3.Error as e:
        logging.error(f"Database error in checkNewUsers: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in checkNewUsers: {e}")

def get_connection_count(port):
    try:
        connections = psutil.net_connections()
        count = 0
        for conn in connections:
            if conn.laddr.port == port and conn.status == 'ESTABLISHED':
                count += 1
        return count
    except Exception as e:
        logging.error(f"Error in get_connection_count: {e}")
        return 0

class AccessChecker(threading.Thread):
    def __init__(self, user):
        threading.Thread.__init__(self)
        self.user = user

    def run(self):
        user_remark = self.user['name']
        user_port = self.user['port']
        while True:
            try:
                connection_count = get_connection_count(user_port)
                if connection_count > _max_allowed_connections:
                    user_remark = user_remark.replace(" ", "%20")
                    requests.get(
                        f"https://api.telegram.org/bot{_telegrambot_token}/sendMessage?"
                        f"chat_id={_telegram_chat_id}&text={user_remark}%20locked"
                    )
                    disableAccount(user_port)
                    logging.warning(f"Inbound with port {user_port} (ID: {self.user['id']}) blocked")
                time.sleep(10)  # Increased sleep time to reduce CPU usage
            except Exception as e:
                logging.error(f"Unexpected error in AccessChecker: {e}")
                break

def init():
    users_list = getUsers()
    with ThreadPoolExecutor(max_workers=5) as executor:  # Limited thread pool
        for user in users_list:
            executor.submit(AccessChecker(user).start())  # Fixed parentheses
            logging.info(f"Starting checker for: {user['name']} (ID: {user['id']})")

# Initialize and start the script
init()
schedule.every(30).minutes.do(checkNewUsers)  # Increased schedule interval

# Main loop
while True:
    schedule.run_pending()
    time.sleep(1)