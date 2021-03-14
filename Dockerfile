FROM python:3.8

COPY ./requirements.txt /requirements.txt

RUN pip3 install -r requirements.txt -i https://pypi.douban.com/simple

RUN pip3 install uwsgi -i https://pypi.douban.com/simple