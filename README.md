v2ray-connection-limiter


Install Guide :
1 - install python .
2 - pip3 install requests and pip3 install schedule
3 - install netstat (if your server doesn't have it so install it - debian : apt install net-tools)
4 - put it on background => nohup python3 main.py & (without background process : python3 main.py)
5 - you can set telegram bot token + your tlg chat_id for notification as well . it's pretty clear on the code .

If you need use to Virtual Environment.
1 - python3 -m venv myenv
2 - source myenv/bin/activate
3 - pip install requests schedule
