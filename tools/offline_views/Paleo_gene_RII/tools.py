#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import sys
import shutil
import subprocess
import traceback

# =========================================================
# 1. 基础路径配置
# =========================================================

def get_real_base_dir():
    """
    获取项目根目录 (manage.py 所在位置)。
    适配深层嵌套目录结构：.../tools/offline_views/Paleo_gene_RII/tools.py
    """
    current_path = os.path.abspath(os.path.dirname(__file__))
    
    # 向上查找范围增加到 6 层，确保能从深层目录找到根目录
    for _ in range(6):
        if os.path.exists(os.path.join(current_path, "manage.py")):
            return current_path
        parent = os.path.dirname(current_path)
        if parent == current_path: # 到达系统根目录
            break
        current_path = parent
    
    # 如果找不到 manage.py，为了防止报错，尝试使用硬编码的回退策略
    # 假设 tools.py 在 .../tools/offline_views/Paleo_gene_RII/
    # 我们需要回退 3 层到达 Asteraceae
    fallback_path = os.path.abspath(os.path.dirname(__file__)) # Paleo_gene_RII
    for _ in range(3):
        fallback_path = os.path.dirname(fallback_path)
    return fallback_path

BASE_DIR = get_real_base_dir()

# =========================================================
# 2. 关键修复：智能获取 Python 解释器路径
# =========================================================

def get_python_executable():
    """
    获取真正的 Python 解释器路径。
    解决在 uWSGI 环境下 sys.executable 指向 uwsgi 二进制文件的问题。
    """
    executable = sys.executable

    # 如果 sys.executable 包含 'uwsgi'，说明我们处于 uWSGI 环境中
    if 'uwsgi' in executable.lower():
        print(f"⚠️ [Tools] Detected uWSGI environment. sys.executable is: {executable}")
        
        # 尝试从 sys.exec_prefix (虚拟环境根目录) 拼接 python 路径
        # Linux 虚拟环境通常在 <venv>/bin/python
        venv_python = os.path.join(sys.exec_prefix, 'bin', 'python')
        
        if os.path.exists(venv_python):
            return venv_python
        
        # 如果找不到，尝试 python3 系统命令
        return 'python3'
    
    return executable

PYTHON_EXE = get_python_executable()

print(f"✅ [Tools] Base Dir (Project Root): {BASE_DIR}")
print(f"✅ [Tools] Real Python Exe: {PYTHON_EXE}")

# =========================================================
# 3. 核心业务逻辑
# =========================================================

def zu_loss_run_tools(place):
    """
    执行 Gene Loss 核心分析任务
    :param place: 任务 ID (file_keep 下的文件夹名)
    """
    # 1. 定义路径
    # work_dir 位于根目录下的 file_keep 文件夹中
    work_dir = os.path.join(BASE_DIR, 'file_keep', place)
    
    # 获取 tools.py 当前所在的目录 (Paleo_gene_RII)
    current_tool_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = 'lost.py'
    
    # 在当前目录下找 lost.py
    source_script = os.path.join(current_tool_dir, script_name)

    print(f"🔎 [Tools] Looking for script at: {source_script}")

    # 2. 预检
    if not os.path.exists(source_script):
        error_msg = f"❌ Core script missing: {source_script}\nMake sure lost.py and tools.py are in the same directory."
        print(error_msg)
        raise FileNotFoundError(error_msg)
    
    if not os.path.exists(work_dir):
        error_msg = f"❌ Working directory missing: {work_dir}"
        print(error_msg)
        raise FileNotFoundError(error_msg)

    # 3. 复制脚本到工作目录
    target_script = os.path.join(work_dir, script_name)
    try:
        shutil.copy(source_script, target_script)
    except Exception as e:
        print(f"❌ Copy script failed: {e}")
        raise e

    # 4. 创建输出目录 (虽然 lost.py 也会建，但双重保险)
    output_dir = os.path.join(work_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)

    print(f"🚀 [Tools] Executing {script_name} in {work_dir}...")

    # 5. 执行脚本
    try:
        # 使用修正后的 PYTHON_EXE
        cmd = [PYTHON_EXE, script_name]
        
        result = subprocess.run(
            cmd, 
            cwd=work_dir,           # 设定工作目录
            check=True,             # 关键：如果脚本返回非0状态码，这里会抛出 CalledProcessError
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,             
            encoding='utf-8',       
            errors='ignore'        
        )
        
        # 打印脚本的标准输出到控制台，方便调试
        if result.stdout:
            print(f"[{script_name} STDOUT]:\n{result.stdout}")
            
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ Script Execution Failed!\nReturn Code: {e.returncode}\nError Output:\n{e.stderr}"
        print(error_msg)
        # 向上抛出异常，让 views.py 捕获并显示给用户
        raise RuntimeError(error_msg)
        
    except Exception as e:
        traceback.print_exc()
        raise e

    print(f"✅ [Tools] Task {place} finished successfully.")