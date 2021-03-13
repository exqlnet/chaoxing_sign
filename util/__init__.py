from flask_restful import reqparse


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
