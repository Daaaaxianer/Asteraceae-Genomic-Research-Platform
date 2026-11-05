#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import sys
import subprocess
import glob
import zipfile
import traceback
import time
import random
import string

# =========================================================
# 1. 核心路径配置 (离线环境适配)
# =========================================================

# 当前文件: .../Asteraceae/tools/offline_views/GF_Circos/tools.py
current_file_path = os.path.abspath(__file__)
gf_circos_dir = os.path.dirname(current_file_path)     # .../GF_Circos
offline_views_dir = os.path.dirname(gf_circos_dir)     # .../offline_views
tools_dir = os.path.dirname(offline_views_dir)         # .../tools
path_get = os.path.dirname(tools_dir)                  # .../Asteraceae (项目根目录)

print(f"✅ [Tools] Project Root: {path_get}")
print(f"✅ [Tools] GF_Circos Dir: {gf_circos_dir}")

# =========================================================
# 【修复点】uWSGI 兼容性处理
# =========================================================
def get_python_executable():
    """
    获取真实的 Python 解释器路径。
    解决在 uWSGI 下 sys.executable 指向 uwsgi 二进制文件的问题。
    """
    executable = sys.executable
    
    # 如果 sys.executable 包含 'uwsgi'，说明是被 uWSGI 劫持了
    if 'uwsgi' in executable.lower():
        # 尝试通过 sys.prefix (当前环境/虚拟环境根目录) 找到 python
        # Linux/Mac 下通常在 bin/python，Windows 下在 Scripts/python.exe
        possible_paths = [
            os.path.join(sys.prefix, 'bin', 'python'),
            os.path.join(sys.prefix, 'bin', 'python3'),
            os.path.join(sys.prefix, 'Scripts', 'python.exe'),
        ]
        
        for p in possible_paths:
            if os.path.exists(p):
                print(f"⚠️ [Tools] Detect uWSGI env. Switched python exe to: {p}")
                return f'"{p}"' #以此路径执行
        
        # 如果找不到绝对路径，回退到系统命令 'python'
        print("⚠️ [Tools] Detect uWSGI env but cannot find python binary. Using 'python' command.")
        return "python"
        
    return f'"{executable}"'

# 获取正确的 Python 命令
PYTHON_EXE = get_python_executable()

# =========================================================
# 2. 文件与目录辅助函数
# =========================================================

def name_set():
    """生成随机目录名"""
    c = ''.join(random.sample(string.digits, 9))
    target = os.path.join(path_get, 'file_keep', c)
    from api.download_access import create_job_directory
    create_job_directory(target)
    return c

def text_create(name, msg, place):
    """生成配置文件"""
    desktop_path = os.path.join(path_get, 'file_keep', place)
    os.makedirs(desktop_path, exist_ok=True)
    full_path = os.path.join(desktop_path, name + '.conf')
    # 强制使用 UTF-8 编码
    with open(full_path, 'w', encoding='utf-8') as file:
        file.write(msg)

# =========================================================
# 3. 核心业务逻辑
# =========================================================

def GF_ks_circos_run_tools(place, sp_name):
    """
    生成配置文件并调用外部绘图脚本
    :param place: 工作目录 ID (file_keep 下的文件夹名)
    :param sp_name: 物种前缀 (如 Sob)
    """
    work_dir = os.path.join(path_get, 'file_keep', place)
    os.makedirs(work_dir, exist_ok=True)

    # 1. 构建配置文件内容
    conf_content = f"""[excircle]
savefig = {sp_name}.genefam.png
specieslist = {sp_name}
lens_file = {sp_name}.lens.txt
gff_file = {sp_name}.new.gff
ks_file = {sp_name}_{sp_name}.ks.txt
pair_file = {sp_name}.pair
classifyfile  = {sp_name}.class
classify_color = 1:#CC99FF,2:orange,3:#FF1493,4:red,5:blue,6:c,7:black
young_genes_ks = #
young_genes_color = #
axes_limit = 0.9
alpha = 0.7
line_color = #dcdcdd
label_pos = 0.85
dpi = 600
"""

    # 2. 写入配置文件
    conf_name = f'excircle_{sp_name}'
    text_create(conf_name, conf_content, place)

    # 3. 定位启动脚本 (已指向当前 GF_Circos 目录下的 run.py)
    script_path = os.path.join(gf_circos_dir, 'run.py')
    
    if not os.path.exists(script_path):
        print(f"❌ Error: Script not found at {script_path}")
        print(f"   Searching in: {gf_circos_dir}")
        return

    # 4. 构建命令行指令
    # 使用修正后的 PYTHON_EXE
    cmd = f'{PYTHON_EXE} "{script_path}" excircle -c "{conf_name}.conf"'
    
    print(f"🔄 Executing: {cmd}") # 调试日志
    
    # 5. 执行子进程
    try:
        # cwd 设置为工作目录，这样脚本生成的图片会直接保存在 file_keep/xxx 下
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=work_dir, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Plotting Failed:\n{result.stderr}")
            raise Exception(f"Plotting script failed: {result.stderr}")
        else:
            print(f"✅ Plotting Success:\n{result.stdout}")
            
    except Exception as e:
        traceback.print_exc()
        raise e