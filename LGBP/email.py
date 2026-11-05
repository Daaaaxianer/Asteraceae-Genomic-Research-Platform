import os
#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :email.py
# @Time :2022/1/14 22:05

import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


def youjian(a, b, place):
    """
    此模块用于 用户邮件的发送
    a：用户邮件地址
    b：所发送附件的地址
    place：验证码  （文件所保存的文件夹的位置）
    """

    # noinspection PyGlobalUndefined
    def read_emall(place):
        global path_get
        with open(f'{path_get}/file_keep/{place}/email.txt', 'r+') as f:
            return f.read()
    if a is None:
        a = read_emall(place)
    else:
        a = a
    fromaddr = os.environ.get('AGRP_SMTP_FROM', '')  # 发邮件的信箱
    password = os.environ.get('AGRP_SMTP_PASSWORD', '')  # 邮箱的授权码
    toaddrs = ['%s' % a]
    content = 'This is the result of your processing.'  # 邮件内容
    textApart = MIMEText(content)
    imageFile = '%s' % b
    imageApart = MIMEImage(open(imageFile, 'rb').read(), imageFile.split('.')[-1])
    imageApart.add_header('Content-Disposition', 'attachment', filename=imageFile)
    m = MIMEMultipart()
    m.attach(imageApart)
    m.attach(textApart)
    m['Subject'] = 'THE GEFA processing results'  # 邮件标题
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(fromaddr, password)
        server.sendmail(fromaddr, toaddrs, m.as_string())
        server.quit()
    except smtplib.SMTPException as e:
        print('error:', e)  # 打印错误










