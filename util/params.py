from flask_restful import reqparse
from werkzeug import exceptions
from functools import wraps


def add_args(li, location='json'):
    """add resource reqparse argument from list"""

    res = reqparse.RequestParser()
    for s in li:
        res.add_argument(s[0],
                         type=s[1],
                         required=s[2],
                         help=s[3],
                         location=location)
    return res


def params(params_list, location="json", empty_check=True):
    """
    用法
    class A(Resource):
        @params([
            ["arg1", str, True, "arg1 helper goes here"],
            ["arg2", str, True, "arg2 helper goes here"],
        ], location="json", empty_check=True)
        def post(self, arg1, arg2):
            pass
    :param params_list: 参数列表
    :param location: 在get请求默认是args(query string), 在其他请求是json
    :param empty_check: 默认对str类型且标记为True的字符串进行空字符串(““)的检查， 设置empty_check=False进行关闭
    :return:
    """

    def decorator(func):
        nonlocal location
        if func.__name__ == "get":
            location = "args"
        if empty_check:
            # 获取需要检查的字段
            to_checks = []
            for arg in params_list:
                if arg[1] is str and arg[2] is True:
                    to_checks.append(arg[0])

        @wraps(func)
        def inner(*args, **kwargs):
            try:
                a = add_args(params_list, location).parse_args()
            except exceptions.BadRequest as e:
                e.data["status"] = 0
                raise e
            else:
                if empty_check:
                    for to_check in to_checks:
                        if not a[to_check]:
                            return {"message": "{0} can not be empty!".format(to_check), "status": 0}, 400
                kwargs.update(a)
            return func(*args, **kwargs)

        return inner

    return decorator
