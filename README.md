v2ray-connection-limiter

Original Creator - https://github.com/net-pioneer/v2ray-connection-limiter and I refer to edit code.

Install Guide :

1 - install python.

2 - pip3 install requests and pip3 install schedule

3 - install netstat (if your server doesn't have it so install it - Debian : apt install net-tools)

4 - put it on background => nohup python3 main.py & (without background process : python3 main.py)

5 - you can also set the telegram bot token + your tlg chat_id for notification. it's pretty clear on the code.

If you need to use Virtual Environment.

1 - python3 -m venv myenv  #if you need to install apt install python3.10-venv

2 - source myenv/bin/activate

3 - pip install requests schedule
