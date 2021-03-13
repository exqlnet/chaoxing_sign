# -*- coding: utf8 -*-
import json
from cx import AutoSign
from log import logging


def main_handler(event, context):
    if event.get("Type") != "Timer":
        return "非定时触发"
    params = json.loads(event["Message"])
    username = params["username"]
    password = params["password"]
    server_chan_key = params["sckey"]
    is_send_server_chan = True if params["send_wechat"] == "True" else "False"
    s = AutoSign(username, password, server_chan_key, redis_host="<redis-host>", redis_port=6379)
    result = s.sign_tasks_run()
    if result:
        if is_send_server_chan:
            s.server_chan_send(result)
        logging.info(result)
        return s.username + " sign in success!"
    else:
        return s.username + " no tasks."
