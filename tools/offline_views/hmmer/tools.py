#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :tools.py
# @Time :2022/1/14 22:04
# Written by Yu Zijian
# E-main: yuzijian1010@163.com

import os
import re
import time
import glob
import sys
import csv
import pylab
import random
import shutil
import string
import pymysql
import subprocess
import numpy as np
import pandas as pd
from ete3 import Tree
from Bio import SeqIO, Phylo, Entrez
from .email import youjian
from functools import reduce
from django.http import HttpResponse
from django.core.files import File
from django.shortcuts import render
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures
from django import forms


path_get = os.getcwd()


# 在文件夹内 创建文件夹
def keep_in_file(na, c, fg=None):
    cmd = '''
        cd %s/file_keep/%s
        mkdir all_file
    ''' % (path_get, c)
    os.system(cmd)

    with open('%s' % os.path.join(f'{path_get}/file_keep/{c}/all_file/', na.name), 'wb') as f:
        for chunk1 in na.chunks():
            f.write(chunk1)
    f.close()


# 保存单个文件
def keep_file(na, c, fg=None):
    if fg is None:
        pass
    else:
        nam = na.name.split(".")
        na.name = nam[0]

    # 被我保存到本地啦，保存到哪里随意啦
    with open(f"{path_get}/file_keep/{c}/{na.name}", 'wb+') as f:
        for chunk1 in na.chunks():
            f.write(chunk1)
    f.close()


# 创建conf配置文件
def text_create(name, msg, place):
    desktop_path = f"{path_get}/file_keep/{place}/"  # 新创建的txt文件的存放路径
    full_path = desktop_path + name + '.conf'  # 也可以创建一个.doc的word文档
    file = open(full_path, 'w')
    file.write(msg)  # msg也就是下面的Hello world!
    file.close()


# 保存多个文件
# def keep_files(na, c, fg=None, ret_files=None):
#     cmd = f'''
#         cd {path_get}/file_keep/{c}
#         mkdir orthomcl
#     '''
#     os.system(cmd)
#
#     for file in na:
#         with open('%s' % os.path.join(f'{path_get}/file_keep/{c}/orthomcl/', file.name), 'wb') as f:
#             for i in file.chunks():
#                 f.write(i)
def keep_files(na, c):
    destination_path = os.path.join(path_get, 'file_keep', c, 'orthomcl')
    os.makedirs(destination_path, exist_ok=True)

    for file in na:
        destination_file_path = os.path.join(destination_path, file.name)
        with open(destination_file_path, 'wb') as destination_file, file.open('rb') as source_file:
            shutil.copyfileobj(source_file, destination_file)


# 此模块用于检查 文件是否存在 （b，c，d 参数未补全）
#     e ：文件夹名字
def name_check(e):
    """
    此模块用于检查 文件是否存在 （b，c，d 参数未补全）
    e ：文件夹名字
    """
    global path_get

    a = os.path.isfile('/home/a123123/PycharmProjects/untitled2/file_keep/%s/1.FASTA' % e)
    b = os.path.isfile('/home/a123123/PycharmProjects/untitled2/file_keep/%s/email.txt' % e)
    c = os.path.isfile('/home/a123123/PycharmProjects/untitled2/file_keep/%s/email.txt' % e)
    d = os.path.isfile('/home/a123123/PycharmProjects/untitled2/file_keep/%s/email.txt' % e)
    n = ''
    if b:
        n = '1.FASTA'
    elif a:
        n = 'd'
    elif a:
        n = 'd'
    elif a:
        n = 'd'
    return n


def name_set():
    """ 在file_keep中创建文件夹
    :return: c 随机文件夹名字
    """
    c = ''.join(random.sample(string.digits, 9))
    from api.download_access import create_job_directory
    create_job_directory(f'file_keep/{c}')
    return c


def zip_file(place, email, files):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        zip -r result.zip {files}
    """
    os.system(cmd)

    g = f'{path_get}/file_keep/{place}/result.zip'





# hmmer
def hmmer_run_tools(place, e_value):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        hmmbuild db_model.hmm hmm_model.fasta
        hmmsearch -o result.out --noali -E {e_value} db_model.hmm hmm_fa.fasta
    """
    os.system(cmd)
