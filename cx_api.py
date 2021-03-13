from flask import Flask, request
import json
from flask_restful import Resource, Api
from util.params import params
from cx import AutoSign
from threading import Thread
import copy
from config import config
from flask_cors import CORS


def get_users():
    with open("account.json", "r") as f:
        users = json.load(f)
    api_key = request.headers.get("api-key")
    if not api_key:
        return []
    users = list(filter(lambda u: u.get("api_key") == api_key, users))
    return users


class ScanSign(Resource):

    def get(self):
        users = get_users()
        return [{
            "name": user["name"],
            "username": user["username"],
        } for user in users]

    @params([
        ["sign_users", list, True, "sign users can not be null"],
        ["enc", str, True, "enc can not be null"]
    ])
    def post(self, sign_users, enc):
        users = get_users()
        valid_usernames = set([user['username'] for user in users])
        sign_users = valid_usernames & set(sign_users)
        tasks = []
        result = []
        for user in users:
            if user["username"] in sign_users:
                def _sign(_user):
                    cx = AutoSign(_user["username"], _user["password"], user["sckey"], **config)
                    r = cx.sign_tasks_run(enc=enc)
                    if r:
                        # 签到成功
                        result.append({"name": _user["name"], "username": _user["username"]})
                thr = Thread(target=_sign, args=(copy.deepcopy(user),))
                thr.start()
                tasks.append(thr)
        for task in tasks:
            task.join()
        return result


app = Flask(__name__, static_folder="dist")


@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file(path)


@app.route('/')
def index():
    return app.send_static_file("index.html")


CORS(app)
api = Api(app)
api.add_resource(ScanSign, "/api/scan")

if __name__ == "__main__":
    app.run(host="0.0.0.0")
