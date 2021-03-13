# -*- coding: utf8 -*-
import urllib3
import asyncio
import re
import json
import requests
from bs4 import BeautifulSoup
from redis import Redis
from log import logging
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AutoSign(object):

    def __init__(self, username, password,
                 sckey, schoolid=None,
                 redis_host="redis", redis_db=0, redis_port=6379, redis_pass=None):
        """初始化就进行登录"""
        self.headers = {
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36'}
        self.session = requests.session()
        self.session.headers = self.headers
        self.username = username
        self.sckey = sckey
        self.cache = Redis(host=redis_host, db=redis_db, password=redis_pass, port=redis_port)
        if not self.check_cookies_status():
            self.login(password, schoolid, username)
            self.save_cookies()
    
    def log(self, msg):
        logging.info(f"{self.username}: {msg}")

    def save_cookies(self):
        """保存cookies"""
        new_cookies = self.session.cookies.get_dict()
        self.cache.set(self.username + "_cookies", json.dumps(new_cookies), ex=3 * 24 * 60)

    def check_cookies_status(self):
        """检测json文件内是否存有cookies,有则检测，无则登录"""
        cookies_byte = self.cache.get(self.username + "_cookies")
        if not cookies_byte:
            return False
        cookies = json.loads(cookies_byte.decode())
        # 找到后设置cookies
        for u in cookies:
            self.session.cookies.set(u, cookies[u])

        # 检测cookies是否有效
        r = self.session.get('http://mooc1-2.chaoxing.com/visit/interaction', allow_redirects=False)
        # todo 尚不清楚为啥这里200了，后面获取课程还会跳转登陆
        # 换了个URL、增加了匹配方式，临时解决方案
        if r.status_code != 200 or "登陆" in r.text:
            self.log("cookies已失效，重新获取中")
            return False
        else:
            self.log("cookies有效哦")
            return True

    def login(self, password, schoolid, username):
        # 登录-手机邮箱登录
        if schoolid:
            r = self.session.post(
                'http://passport2.chaoxing.com/api/login?name={}&pwd={}&schoolid={}&verify=0'.format(username, password,
                                                                                                     schoolid))
            if json.loads(r.text)['result']:
                self.log("登录成功")
                return True
            else:
                logging.fatal("登录失败，请检查账号密码是否正确")
                return False

        else:
            r = self.session.get(
                'https://passport2.chaoxing.com/api/login?name={}&pwd={}&schoolid=&verify=0'.format(username, password),
                headers=self.headers)
            if json.loads(r.text)['result']:
                self.log("登录成功")
                return True
            else:
                self.log("登录失败，请检查账号密码是否正确")
                return False

    def check_activeid(self, activeid):
        """检测activeid是否存在，不存在则添加"""
        key = self.username + "_activeid"
        if self.cache.sismember(key, activeid):
            return True
        else:
            return False

    def sign_success(self, checkin):
        key = self.username + "_activeid"
        self.cache.sadd(key, checkin["activeid"])
        desp = f'**🐂课程名**：{checkin["classname"]}	\r'
        desp += f'**🍻签到时间**：{datetime.now()}	\r'
        desp += f'**✊签到状态**：{"签到成功"}	\r'
        desp += f'**👋签到账号**：{self.username}	\r'
        desp += f'**👮签到类型**：{checkin["sign_type"]}'
        self.server_chan_send(desp)

    def get_all_classid(self) -> list:
        """获取课程主页中所有课程的classid和courseid"""
        r = self.session.get(
            'http://mooc1-2.chaoxing.com/visit/interaction',
            headers=self.headers)
        soup = BeautifulSoup(r.text, "html.parser")
        course_list = soup.select("li.courseItem")
        class_course_list = []
        for course in course_list:
            class_name = course.select("div.Mconright.httpsClass > h3 > a")[0].text
            course_id = course.select("input[type=hidden]:nth-child(1)")[0].get("value")
            class_id = course.select("input[type=hidden]:nth-child(2)")[0].get("value")
            class_course_list.append([course_id, class_id, class_name])
        return class_course_list

    async def get_activeid(self, classid, courseid, classname):
        """访问任务面板获取课程的活动id"""
        # sign_re_rule = r'<div class="Mct" onclick="activeDetail\((.*),2,null\)">[\s].*[\s].*[\s].*[\s].*<dd class="green">.*</dd>'
        # sign_type_re_rule = r'<a href="javascript:;" shape="rect">\[(.*)\]</a>'
        re_rule = r'<div class="Mct" onclick="activeDetail\((.*),2,null\)">[\s].*[\s].*[\s].*[\s].*<dd class="green">.*</dd>[\s]+[\s]</a>[\s]+</dl>[\s]+<div class="Mct_center wid660 fl">[\s]+<a href="javascript:;" shape="rect">(.*)</a>'
        res = self.session.get(
            'https://mobilelearn.chaoxing.com/widget/pcpick/stu/index?courseId={}&jclassId={}'.format(
                courseid, classid), headers=self.headers, verify=False)
        checks = re.findall(re_rule, res.text)

        result = []
        # 获取签到类型
        for check in checks:
            res = self.session.get(f"https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/preSign?activeId={check[0]}&classId={classid}&fid=262&courseId={courseid}")
            result.append({
                'classid': classid,
                'courseid': courseid,
                'activeid': check[0],
                'classname': classname,
                'sign_type': re.findall("<title>(.+?)</title>", res.text)[0],
            })

        result = sorted(result, reverse=True, key=lambda k: k['activeid'])
        return result

    def general_sign(self, classid, courseid, activeid):
        """普通签到"""
        res = self.session.get(
            'https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/preSign?activeId={}&classId={}&fid=39037&courseId={}'.format(
                activeid, classid, courseid), headers=self.headers, verify=False)
        title = re.findall('<title>(.*)</title>', res.text)[0]
        if "签到成功" not in title:
            # 网页标题不含签到成功，则为拍照签到
            return self.tphoto_sign(activeid)
        else:
            if "失败" in res.text:
                self.log(res.text)
                return False
            return True

    def hand_sign(self, classid, courseid, activeid):
        """手势签到"""
        hand_sign_url = "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/signIn?&courseId={}&classId={}&activeId={}".format(
            courseid, classid, activeid)
        res = self.session.get(hand_sign_url, headers=self.headers, verify=False)
        if "失败" in res.text:
            self.log(res.text)
            return False
        return True

    def addr_sign(self, activeId):
        """位置签到"""
        params = {
            'name': '',
            'activeId': activeId,
            'address': '',
            'uid': '',
            'clientip': '0.0.0.0',
            'longitude': '0',
            'latitude': '0',
            'fid': '',
            'appType': '15',
            'ifTiJiao': '1'
        }
        res = self.session.get('https://mobilelearn.chaoxing.com/pptSign/stuSignajax', params=params)
        if "失败" in res.text:
            self.log(res.text)
            return False
        return True

    def qcode_sign(self, activeId, enc=""):
        """二维码签到"""
        if not enc:
            return False
        params = {
            'enc': enc,
            'name': '',
            'activeId': activeId,
            'uid': '',
            'clientip': '',
            'useragent': '',
            'latitude': '-1',
            'longitude': '-1',
            'fid': '',
            'appType': '15'
        }
        res = self.session.get('https://mobilelearn.chaoxing.com/pptSign/stuSignajax', params=params)
        if "失败" in res.text:
            self.log(res.text)
            return False
        return True

    def tphoto_sign(self, activeId):
        """拍照签到"""
        params = {
            'name': '',
            'activeId': activeId,
            'address': '中国',
            'uid': '',
            'clientip': '0.0.0.0',
            'latitude': '-2',
            'longitude': '-1',
            'fid': '',
            'appType': '15',
            'ifTiJiao': '1',
            'objectId': '5712278eff455f9bcd76a85cd95c5de3'
        }
        res = self.session.get('https://mobilelearn.chaoxing.com/pptSign/stuSignajax', params=params)
        if "失败" in res.text:
            self.log(res.text)
            return False
        return True

    def sign_in(self, classid, courseid, activeid, sign_type, **kwargs):
        """签到类型的逻辑判断"""
        if self.check_activeid(activeid):
            return
        if "手势" in sign_type:
            # test:('拍照签到', 'success')
            return self.hand_sign(classid, courseid, activeid)

        elif "二维码" in sign_type:
            return self.qcode_sign(activeid, **kwargs)

        elif "位置" in sign_type:
            return self.addr_sign(activeid)

        else:
            # '[2020-03-20 14:42:35]-[签到成功]'
            r = self.general_sign(classid, courseid, activeid)
            return r

    def sign_tasks_run(self, **kwargs):
        """开始所有签到任务"""
        tasks = []
        # 获取所有课程的classid和course_id
        classid_courseId = self.get_all_classid()
        # 获取所有课程activeid和签到类型
        for i in classid_courseId:
            coroutine = self.get_activeid(i[1], i[0], i[2])
            tasks.append(coroutine)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(asyncio.gather(*tasks))

        count = 0
        for checkins in result:
            for checkin in checkins:
                if checkin:
                    if self.sign_in(checkin['classid'], checkin['courseid'], checkin['activeid'], checkin['sign_type'], **kwargs):
                        self.sign_success(checkin)
                        count += 1
        return count

    def server_chan_send(self, msg):
        """server酱将消息推送至微信"""
        if not self.sckey:
            return
        params = {
            'text': '{}签到消息'.format(self.username),
            'desp': msg,
        }

        requests.get('https://sc.ftqq.com/{}.send'.format(self.sckey), params=params)
