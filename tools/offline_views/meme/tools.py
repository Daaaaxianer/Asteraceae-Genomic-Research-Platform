#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :tools.py

import os
import random
import shutil
import string
import subprocess
import platform
import zipfile
from django.conf import settings

# ---------------------------------------------------------
# 路径配置 (关键修改)
# ---------------------------------------------------------
# 当前脚本位置: /wangjp/Asteraceae/Asteraceae/tools/offline_views/meme/tools.py
# 目标路径:     /wangjp/Asteraceae/Asteraceae/file_keep

try:
    # 尝试使用 Django 设置
    BASE_DIR = str(settings.BASE_DIR)
except:
    BASE_DIR = None

# 如果 settings 获取失败，或者路径不对，使用相对路径计算作为兜底
if not BASE_DIR:
    current_file_path = os.path.abspath(__file__)           # .../meme/tools.py
    dir_meme = os.path.dirname(current_file_path)           # .../meme
    dir_offline = os.path.dirname(dir_meme)                 # .../offline_views
    dir_tools = os.path.dirname(dir_offline)                # .../tools
    # 这一层就是 /wangjp/Asteraceae/Asteraceae
    BASE_DIR = os.path.dirname(dir_tools)                   

# 定义统一的文件保存路径
FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')

# 打印路径到日志，方便调试 (在 uwsgi log 中查看)
print(f"--- [Tools Config] FILE_KEEP_DIR set to: {FILE_KEEP_DIR} ---")

# ---------------------------------------------------------
# 文件与目录管理
# ---------------------------------------------------------

def name_set():
    """ 
    创建随机命名的工作目录 
    """
    c = ''.join(random.sample(string.digits, 9))
    target_dir = os.path.join(FILE_KEEP_DIR, c)
    from api.download_access import create_job_directory
    create_job_directory(target_dir)
    return c

def keep_file(file_obj, c):
    """
    保存上传的文件，并重命名为 1.fasta 供 MEME 使用
    已修复参数名，确保与 views.py 中的调用一致
    """
    save_path = os.path.join(FILE_KEEP_DIR, c)
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    # 强制重命名为 1.fasta，方便后续命令调用
    full_file_path = os.path.join(save_path, '1.fasta')

    # 使用 'wb+' 写入文件流
    try:
        with open(full_file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
    except Exception as e:
        print(f"Error saving file: {e}")
        raise e

def zip_file(place):
    """
    使用 Python 原生库压缩结果文件
    :param place: 文件夹 ID (c)
    :return: 压缩包的绝对路径
    """
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    zip_filename = 'result.zip'
    zip_path = os.path.join(work_dir, zip_filename)

    # 需要压缩的文件后缀
    target_exts = ('.html', '.png', '.txt', '.xml', '.eps')

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 遍历目录
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    # 排除 zip 本身和输入文件，防止死循环或文件过大
                    if file == zip_filename or file == '1.fasta':
                        continue
                        
                    # 只压缩结果文件 (或者去掉这个 if 压缩所有文件)
                    if file.endswith(target_exts) or 'meme' in file:
                        file_abs_path = os.path.join(root, file)
                        # arcname 确保压缩包内部没有多余的层级路径
                        zf.write(file_abs_path, arcname=file)
        return zip_path
    except Exception as e:
        print(f"Zip Error: {str(e)}")
        return None

# ---------------------------------------------------------
# MEME 核心运行逻辑
# ---------------------------------------------------------

def meme_run_tools(place, patten, motif, motif_num, minw, maxw):
    """
    安全运行 MEME 工具
    """
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    input_file = '1.fasta'
    
    # 检查输入文件是否存在
    if not os.path.exists(os.path.join(work_dir, input_file)):
        raise RuntimeError(f"Input file not found in {work_dir}")

    # MEME 可执行文件路径 (根据你的环境设置)
    meme_exe = "/www/tools/soft_tools/meme" 

    cmd = [
        meme_exe,
        input_file,
        f"-{str(patten).lower()}", # -protein, -dna
        "-oc", ".",                # 输出到当前目录
        "-mod", str(motif),        # zoops, oops, anr
        "-nmotifs", str(motif_num),
        "-minw", str(minw),
        "-maxw", str(maxw)
    ]

    print(f"[MEME Tools] Working Dir: {work_dir}")
    print(f"[MEME Tools] Running: {' '.join(cmd)}")

    try:
        # subprocess.run 是 Python 3.5+ 推荐的方式
        process = subprocess.run(
            cmd,
            cwd=work_dir,      # 切换到工作目录执行
            check=True,        # 如果命令返回非0状态码，抛出异常
            shell=False,       # 关闭 shell 执行，提高安全性！
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
    except subprocess.CalledProcessError as e:
        # 获取错误日志
        error_log = e.stderr.decode(errors='ignore') if e.stderr else "Unknown error"
        print(f"[MEME Error]: {error_log}")
        raise RuntimeError(f"MEME execution failed: {error_log}")
        
    except FileNotFoundError:
        raise RuntimeError(
            f"Command not found: {meme_exe}. Please check the path."
        )
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")

# ---------------------------------------------------------
# 旧辅助函数 (保留以兼容旧代码)
# ---------------------------------------------------------

def keep_in_file(na, c, fg=None):
    target_dir = os.path.join(FILE_KEEP_DIR, c, 'all_file')
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, na.name), 'wb') as f:
        for chunk in na.chunks():
            f.write(chunk)

def keep_files(na, c):
    dest_path = os.path.join(FILE_KEEP_DIR, c, 'orthomcl')
    os.makedirs(dest_path, exist_ok=True)
    for file in na:
        with open(os.path.join(dest_path, file.name), 'wb') as f:
            if hasattr(file, 'chunks'):
                for chunk in file.chunks(): f.write(chunk)
            else:
                shutil.copyfileobj(file, f)

def text_create(name, msg, place):
    full_path = os.path.join(FILE_KEEP_DIR, place, f"{name}.conf")
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(msg)