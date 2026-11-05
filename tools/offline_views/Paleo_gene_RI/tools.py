#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import sys
import shutil
import subprocess
import traceback
import re

# =========================================================
# 1. 基础配置与解释器探测
# =========================================================

CURRENT_APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_APP_DIR)))

def get_real_python_exe():
    """
    智能获取真实的 Python 解释器路径。
    解决 uWSGI 环境下 sys.executable 指向 uwsgi 程序本身的问题。
    """
    current_exe = sys.executable
    
    # 检测是否在 uWSGI 环境下
    if 'uwsgi' in current_exe.lower():
        print(f"⚠️ [System] 检测到运行环境为 uWSGI ({current_exe})，正在修正 Python 路径...")
        
        # 尝试 1: 通过 sys.exec_prefix (虚拟环境根目录) 拼接
        # 常见路径: /path/to/venv/bin/python3
        venv_python = os.path.join(sys.exec_prefix, 'bin', 'python3')
        if os.path.exists(venv_python):
            return venv_python
            
        venv_python_alt = os.path.join(sys.exec_prefix, 'bin', 'python')
        if os.path.exists(venv_python_alt):
            return venv_python_alt
            
        # 尝试 2: 如果找不到，回退到系统命令 'python3' (依赖 PATH)
        return 'python3'
    
    # 如果不是 uWSGI，直接返回当前的 executable
    return current_exe

# 获取正确的解释器
PYTHON_EXE = get_real_python_exe()

print(f"✅ [Tools] 模块位置: {CURRENT_APP_DIR}")
print(f"✅ [Tools] 实际使用的 Python 解释器: {PYTHON_EXE}")

# =========================================================
# 2. 核心功能函数
# =========================================================

def sanitize_script(script_path):
    """
    [保险措施] 强制移除 logging 配置
    """
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        modified = False
        for line in lines:
            if 'logging.config.fileConfig' in line:
                new_lines.append(f"# [AUTO-REMOVED] {line}")
                modified = True
            else:
                new_lines.append(line)
        
        if modified:
            print(f"🛡️ [Security] 自动清理 logging 配置: {script_path}")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
    except Exception:
        pass

def zu_retention_run_tools(place):
    """
    执行保留率分析脚本
    """
    try:
        # 1. 定位工作目录
        work_dir = os.path.join(PROJECT_ROOT, 'file_keep', place)
        if not os.path.exists(work_dir):
            # 备用路径查找
            work_dir = os.path.join(os.path.dirname(CURRENT_APP_DIR), 'file_keep', place)
        
        if not os.path.exists(work_dir):
            raise FileNotFoundError(f"Working directory not found: {work_dir}")

        # 2. 准备目录
        output_dir = os.path.join(work_dir, 'output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        orthomcl_dir = os.path.join(work_dir, 'orthomcl')
        if not os.path.exists(orthomcl_dir):
            os.makedirs(orthomcl_dir)
            # 移动文件
            for item in os.listdir(work_dir):
                item_path = os.path.join(work_dir, item)
                if os.path.isfile(item_path) and not item.endswith('.py'):
                    shutil.move(item_path, os.path.join(orthomcl_dir, item))

        # 3. 准备脚本
        script_name = 'gene_calc.py'
        script_source = os.path.join(CURRENT_APP_DIR, script_name)
        if not os.path.exists(script_source):
            script_source = os.path.join(PROJECT_ROOT, script_name)

        if not os.path.exists(script_source):
            raise FileNotFoundError(f"Source file not found: {script_name}")

        script_dest = os.path.join(work_dir, script_name)
        if os.path.exists(script_dest):
            os.remove(script_dest)
        shutil.copy(script_source, script_dest)

        # 4. 清理并执行
        sanitize_script(script_dest)

        print(f"🚀 [Running] 使用解释器: {PYTHON_EXE}")
        
        # 关键调用：使用探测到的 PYTHON_EXE
        result = subprocess.run(
            [PYTHON_EXE, script_name], 
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode != 0:
            print("❌ 运行失败:")
            print(result.stderr)
            raise RuntimeError(f"Script Failed: {result.stderr}")
        else:
            print("✅ 运行成功")

    except Exception as e:
        traceback.print_exc()
        raise e