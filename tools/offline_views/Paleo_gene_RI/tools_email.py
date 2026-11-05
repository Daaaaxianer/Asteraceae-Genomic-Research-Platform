#!/usr/bin/env python
# -*- coding:utf-8 -*-
# 文件名: tools_email.py

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# 修改处：增加了 place 参数，默认为 None
def youjian(target_email, file_path, place=None):
    """
    target_email: 收件人邮箱
    file_path: 附件的完整路径
    place: 任务ID/文件夹名称 (用于邮件标题区分)
    """
    if not target_email or not file_path:
        print("❌ [Email] 邮箱或文件路径为空，无法发送")
        return

    # --- 配置区域 ---
    fromaddr = os.environ.get('AGRP_SMTP_FROM', '')  # 你的发件邮箱
    password = os.environ.get('AGRP_SMTP_PASSWORD', '')   # 你的授权码
    # ----------------

    # 创建邮件对象
    m = MIMEMultipart()
    m['From'] = fromaddr
    m['To'] = target_email
    
    # 修改处：如果传入了 place (任务ID)，将其加入邮件标题
    if place:
        m['Subject'] = f'Gene Retention Analysis Result - JobID: {place}'
    else:
        m['Subject'] = 'Gene Retention Analysis Result'
    
    # 邮件正文
    content = 'Dear User,\n\nHere is your analysis result (ZIP file).\n\nBest regards,\nAsteraceae Platform'
    m.attach(MIMEText(content, 'plain', 'utf-8'))

    # 添加附件 (ZIP文件专用写法)
    try:
        with open(file_path, 'rb') as f:
            # 使用 MIMEApplication 处理 zip 文件
            part = MIMEApplication(f.read())
            # 提取文件名 (例如 result.zip)
            filename = os.path.basename(file_path)
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            m.attach(part)
    except Exception as e:
        print(f"❌ [Email] 读取附件失败: {e}")
        return

    # 发送邮件
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(fromaddr, password)
        server.sendmail(fromaddr, [target_email], m.as_string())
        server.quit()
        print(f"✅ [Email] 邮件已通过 tools_email.py 发送给 {target_email}")
    except smtplib.SMTPException as e:
        print(f'❌ [Email] 发送报错: {e}')