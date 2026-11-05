#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :cp_file.py
# @Time :2022/7/25 16:28

import os


files = open('name.txt', 'r')

for line in files.readlines():
    print(line.split('\n'))
    line = line.split('\n')[0]

    cmd = f"cp Apr.html {line}.html"
    os.system(cmd)









