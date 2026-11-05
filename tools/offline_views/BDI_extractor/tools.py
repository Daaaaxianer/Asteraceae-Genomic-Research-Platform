#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :tools.py
# Written by Yu Zijian
# E-main: yuzijian1010@163.com

import os
import sys
import time
import glob
import random
import string
import shutil
import zipfile
import traceback
import pandas as pd

from Bio import SeqIO

# =========================================================
# 2. 核心路径配置
# =========================================================

def get_real_base_dir():
    """获取项目根目录 (BDI-EXTRACTOR)"""
    # 假设 tools.py 在 BDI-EXTRACTOR/tools/ 目录下
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

path_get = get_real_base_dir()

# 确保保存文件夹存在
os.makedirs(os.path.join(path_get, 'file_keep'), exist_ok=True)

print(f"✅ [Tools] Tools loaded. Root path: {path_get}")


# =========================================================
# 3. 文件操作辅助函数
# =========================================================

def name_set():
    """生成唯一随机目录名"""
    c = ''.join(random.sample(string.digits, 9))
    target = os.path.join(path_get, 'file_keep', c)
    from api.download_access import create_job_directory
    create_job_directory(target)
    return c

def keep_file(na, c, fg=None):
    """保存上传文件"""
    if not na: return
    
    # 如果有 fg 参数，可能会重命名文件 (保留原逻辑)
    if fg is not None:
        nam = na.name.split(".")
        na.name = nam[0]
        
    target_dir = os.path.join(path_get, 'file_keep', c)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, na.name)
    with open(file_path, 'wb+') as f:
        for chunk in na.chunks():
            f.write(chunk)
    return file_path

def keep_files(na, c):
    """保存多个文件"""
    if not na: return
    target_dir = os.path.join(path_get, 'file_keep', c)
    os.makedirs(target_dir, exist_ok=True)
    
    for file in na:
        file_path = os.path.join(target_dir, file.name)
        with open(file_path, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)

def zip_file(place, email, files):
    """压缩文件 (适配 views.py 的调用)"""
    work_dir = os.path.join(path_get, 'file_keep', place)
    zip_name = os.path.join(work_dir, 'result.zip')
    
    # files 可能是空格分隔的字符串
    file_list = files.split()
    
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_pattern in file_list:
                # 支持通配符匹配
                full_pattern = os.path.join(work_dir, file_pattern)
                for f in glob.glob(full_pattern):
                    if os.path.isfile(f) and f != zip_name:
                        zf.write(f, arcname=os.path.basename(f))
    except Exception as e:
        print(f"Zip error: {e}")
        traceback.print_exc()

# =========================================================
# 4. 业务逻辑函数
# =========================================================

def extr_row_run(place, row_num, row_name, row_last):
    """
    按列提取数据
    Args:
        place: 任务ID (文件夹名)
        row_num: 列号字符串，例如 "1" 或 "1,2,3"
        row_name: 文件名前缀
        row_last: 文件后缀
    """
    work_dir = os.path.join(path_get, 'file_keep', place)
    infile = os.path.join(work_dir, f"{row_name}.{row_last}")
    outfile = os.path.join(work_dir, f"{row_name}.new.{row_last}")
    
    print(f"Running extract on: {infile}")
    print(f"Columns to extract: {row_num}")

    try:
        # 读取文件 (默认制表符分隔，无表头)
        # on_bad_lines='skip' 防止格式错误行导致崩溃
        try:
            df = pd.read_csv(infile, sep='\t', header=None, on_bad_lines='skip')
        except TypeError: 
            # 兼容旧版 pandas
            df = pd.read_csv(infile, sep='\t', header=None, error_bad_lines=False)

        # 解析用户输入的列号 (支持 "1" 或 "1,3,5")
        # 用户输入是 1-based，Pandas 是 0-based，所以需要 -1
        col_indices = []
        if ',' in str(row_num):
            col_indices = [int(x.strip()) - 1 for x in str(row_num).split(',') if x.strip().isdigit()]
        else:
            col_indices = [int(row_num) - 1]

        # 过滤掉超出范围的列索引
        max_col = df.shape[1]
        valid_indices = [i for i in col_indices if 0 <= i < max_col]

        if not valid_indices:
            print("Error: No valid columns found to extract.")
            with open(outfile, 'w') as f:
                f.write("Error: Column index out of range.")
            return

        # 提取并保存
        df_new = df.iloc[:, valid_indices]
        df_new.to_csv(outfile, sep='\t', header=False, index=False)
        print("Extraction successful.")

    except Exception as e:
        print(f"Extraction failed: {e}")
        traceback.print_exc()
        # 生成一个错误文件供用户下载查看
        with open(outfile, 'w') as f:
            f.write(f"Error during extraction: {str(e)}")
