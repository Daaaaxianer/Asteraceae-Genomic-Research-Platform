#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@File    ：much.py
@IDE     ：PyCharm 
@Author  ：YZJ
@Date    ：2022/11/21 20:25 
"""
import shutil
import os
path = os.getcwd()
print(path)

sp_list = ["Bva","Sto","Psa","Aip","Amo","Ahy","Adu","Lal","Lan","Aev","Dod","Lja","Apr","Cca","Gma","Gso","Pvu","Mtr","Car","Mal","Tpr","Tsu","Vra","Ssu"]

for line in sp_list:

    try:
        shutil.copy("Amar.te.html", f"{line}.te.html")
    except:
        pass
    # continue