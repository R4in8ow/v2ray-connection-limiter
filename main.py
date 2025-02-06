import os
import sqlite3
import time
import requests
import threading
import schedule
import json
import logging
from signal import signal, SIGINT

# Load configuration from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

_db_address = config['db_address']
_max_allowed_connections = config['max_allowed_connections']
_user_last_id = config.get('user_last_id', 0)
_telegrambot_token = config['telegrambot_token']
_telegram_chat_id = config['telegram_chat_id']

# Set up logging
logging.basicConfig(
    filename='xui_monitor.log',
    level=logging.INFO,
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
            users_list.append({'name': c[1], 'port': c[2]})
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

def init():
    users_list = getUsers()
    for user in users_list:
        thread = AccessChecker(user)
        thread.start()
        logging.info(f"Starting checker for: {user['name']}")

class AccessChecker(threading.Thread):
    def __init__(self, user):
        threading.Thread.__init__(self)
        self.user = user

    def run(self):
        user_remark = self.user['name']
        user_port = self.user['port']
        while True:
            try:
                netstate_data = os.popen(
                    f"netstat -np 2>/dev/null | grep :{user_port} | "
                    "awk '{if($3!=0) print $5;}' | cut -d: -f1 | sort | uniq -c | sort -nr | head"
                ).read()
                connection_count = len(netstate_data.split("\n")) - 1
                if connection_count > _max_allowed_connections:
                    user_remark = user_remark.replace(" ", "%20")
                    requests.get(
                        f"https://api.telegram.org/bot{_telegrambot_token}/sendMessage?"
                        f"chat_id={_telegram_chat_id}&text={user_remark}%20locked"
                    )
                    disableAccount(user_port)
                    logging.info(f"Inbound with port {user_port} blocked")
                else:
                    time.sleep(2)
            except Exception as e:
                logging.error(f"Unexpected error in AccessChecker: {e}")
                break

# Initialize and start the script
init()
schedule.every(10).minutes.do(checkNewUsers)

# Main loop
while True:
    schedule.run_pending()
    time.sleep(1)