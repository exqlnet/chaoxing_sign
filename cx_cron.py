# -*- coding: utf8 -*-
from cx import AutoSign
import json
import time
from log import logging
from threading import Thread
from config import config

if __name__ == '__main__':
    while True:
        t1 = time.time()

        with open("account.json", "r") as f:
            users = json.load(f)

        thrs = []

        for user in users:
            logging.info("👮‍正在签到账号：" + user["name"])
            s = AutoSign(user["username"], user["password"], user.get("location"),
                         user["sckey"] if user["send_wechat"] else None,
                         photo=user.get("photo"),
                         **config)
            s.name = user["name"]

            thr = Thread(target=s.sign_tasks_run)
            thr.start()
            thrs.append(thr)

        for thr in thrs:
            thr.join()

        logging.info("⌚️本次耗时：" + str(time.time() - t1))
        time.sleep(60)
