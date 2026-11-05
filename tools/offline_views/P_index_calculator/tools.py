# Modified for Offline Desktop App
# Written by Yu Zijian & Refactored for independent deployment

import os
import sys
import shutil
import subprocess
import traceback

# =========================================================
# 1. 路径与环境配置
# =========================================================

def get_real_base_dir():
    """
    获取项目根目录 (用于存放 file_keep 文件夹)
    修正逻辑：适配深层嵌套结构，从 tools/offline_views/Paleo_gene_RII/tools.py 回退到根目录
    """
    # 如果是打包后的环境
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    
    current_file = os.path.abspath(__file__)
    
    # 逐级向上回退 4 层以找到 Asteraceae 根目录
    # 1. .../Paleo_gene_RII (当前文件所在目录)
    # 2. .../offline_views
    # 3. .../tools
    # 4. .../Asteraceae (目标根目录)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))

# 全局变量：当前工作根目录 (用于存放 file_keep)
PATH_GET = get_real_base_dir()

# =========================================================
# 2. 核心业务逻辑
# =========================================================

def zu_pindex_run_tools(place, sliding_window, buchang, sigema_start, sigema_end):
    """
    执行 P-index 计算脚本
    """
    work_dir = "" 
    try:
        # 1. 定义工作目录 (file_keep/任务ID)
        # 这里的 PATH_GET 已经是根目录了，所以 file_keep 会生成在 /wangjp/Asteraceae/Asteraceae/file_keep
        work_dir = os.path.join(PATH_GET, 'file_keep', place)
        os.makedirs(work_dir, exist_ok=True)

        # ================= [核心修改] =================
        # 2. 定位核心算法脚本 (p_index.py)
        # 修改为：在当前 tools.py 所在的同一个文件夹内寻找 p_index.py
        current_tool_dir = os.path.dirname(os.path.abspath(__file__))
        script_source = os.path.join(current_tool_dir, 'p_index.py')
        # ============================================

        script_target = os.path.join(work_dir, 'p_index.py')

        if not os.path.exists(script_source):
            error_msg = f"Critical Error: 'p_index.py' not found at {script_source}"
            print(error_msg)
            # 尝试写入错误日志
            with open(os.path.join(work_dir, 'pindex_result.txt'), 'w', encoding='utf-8') as f:
                f.write(error_msg)
            return

        # 3. 复制脚本到临时工作目录（物理隔离，避免并发冲突）
        shutil.copy(script_source, script_target)

        # 4. 创建输出目录
        os.makedirs(os.path.join(work_dir, 'output'), exist_ok=True)

        # 5. 构建命令（使用列表形式，自动处理路径空格）
        # 使用 sys.executable 确保调用的是当前环境的 Python
        cmd = [
            sys.executable,
            "p_index.py",
            str(sliding_window),
            str(buchang),
            str(sigema_start),
            str(sigema_end)
        ]

        # 6. 配置子进程：隐藏 CMD 黑色窗口 (Windows 专有)
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        print(f"[*] Running core analysis in: {work_dir}")

        # 7. 执行计算
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            startupinfo=startupinfo  # 应用隐藏窗口配置
        )

        # 8. 写入执行日志
        log_file = os.path.join(work_dir, 'pindex_result.txt')
        with open(log_file, 'w', encoding='utf-8') as f:
            if result.stdout:
                f.write(result.stdout)
            if result.stderr:
                f.write("\n\n=== RUNTIME ERROR LOG ===\n")
                f.write(result.stderr)
                print("[-] Script Error Output:", result.stderr)

    except Exception as e:
        traceback.print_exc()
        try:
            if work_dir and os.path.exists(work_dir):
                with open(os.path.join(work_dir, 'pindex_result.txt'), 'a', encoding='utf-8') as f:
                    f.write(f"\n[System Error] Tools Execution Failed: {str(e)}")
        except:
            pass