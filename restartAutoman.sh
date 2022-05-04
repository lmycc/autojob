#!/bin/bash
:>uwsgi.log
:>./autojob_log/autojob_info.log
:>./autojob_log/autojob_error.log
source /Users/liumy/PycharmProjects/autojob/venv/bin/activate
uwsginum=`ps -ef |grep -w uwsgi|grep -v grep|wc -l`
nginxnum=`ps -ef |grep -w nginx|grep -v grep|wc -l`
if [ $uwsginum -le 0 ];then
    uwsgi -x autojob.xml
else
    killall -9 uwsgi
    sleep 1s
    uwsgi -x autojob.xml
fi
if [ $nginxnum -le 0 ];then
    nginx
else
    nginx -s reload
fi
curl http://127.0.0.1:80/login/?next=/ >/dev/null