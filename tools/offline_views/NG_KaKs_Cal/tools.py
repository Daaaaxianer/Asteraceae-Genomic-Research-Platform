#!/usr/bin/env python
# -*- coding:utf-8 -*-
# tools.py
import os
import sys
import glob
import shutil
import subprocess
import traceback
from django.conf import settings

# =========================================================
# 1. 基础配置 (用户可修改区域)
# =========================================================

# 【关键修改】如果你知道 perl.exe 在哪，请在这里填入包含 perl.exe 的文件夹路径
# 例如: MANUAL_PERL_PATH = r"C:\Strawberry\perl\bin"
# 如果留空 (None)，脚本将尝试自动搜索
MANUAL_PERL_PATH = "/usr/bin/perl"

# 当前脚本所在目录 (NG-KaKs-Cal)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 向上推3层找到项目根目录 (big_tools_test)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../"))

# 设置结果保存目录
FILE_KEEP_DIR = os.path.join(PROJECT_ROOT, 'file_keep')

# Python解释器路径
PYTHON_EXE = "/usr/bin/python"

# =========================================================
# 2. 智能 Perl 定位 (增强版)
# =========================================================

def find_perl_path():
    """
    寻找包含 perl.exe 的 bin 目录路径
    """
    # 1. 优先使用手动配置
    if MANUAL_PERL_PATH and os.path.exists(os.path.join(MANUAL_PERL_PATH, 'perl.exe')):
        print(f"✅ Using Manual Perl Config: {MANUAL_PERL_PATH}")
        return MANUAL_PERL_PATH

    # 2. 候选路径列表 (增加更多常见位置)
    candidates = [
        # 项目内的可能位置
        os.path.join(PROJECT_ROOT, 'perl_embed', 'bin'),
        os.path.join(PROJECT_ROOT, 'perl_embed', 'perl', 'bin'),
        os.path.join(PROJECT_ROOT, 'perl', 'bin'),              # 新增: 常见的 perl 文件夹名
        os.path.join(PROJECT_ROOT, 'tools', 'perl_embed', 'bin'),
        
        # 常见的 Windows 安装位置
        r"C:\Strawberry\perl\bin",
        r"C:\Perl64\bin",
        r"C:\Perl\bin",
        
        # 兼容旧代码位置
        os.path.join(os.path.dirname(CURRENT_DIR), 'perl_embed', 'bin'),
    ]

    print("--- Searching for Perl ---")
    for path in candidates:
        perl_exe = os.path.join(path, 'perl.exe')
        if os.path.exists(perl_exe):
            print(f"✅ Found Perl at: {path}")
            return path
            
    # 3. 检查系统环境变量
    try:
        # 尝试直接运行 perl -v 看看系统能不能找到
        subprocess.run(["perl", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("✅ Perl found in System PATH")
        return None # 返回 None 表示不需要额外添加路径，直接用系统的
    except:
        pass

    print("⚠️  CRITICAL: Perl not found in project folders or system PATH.")
    return None

# =========================================================
# 3. 工具函数
# =========================================================

def safe_decode(bytes_data):
    """兼容 Windows 中文环境的解码函数"""
    if not bytes_data: return ""
    try: return bytes_data.decode('utf-8')
    except UnicodeDecodeError:
        try: return bytes_data.decode('gbk')
        except: return bytes_data.decode('utf-8', errors='ignore')

def get_tool_path(tool_name):
    local_tool = os.path.join(CURRENT_DIR, f"{tool_name}.exe")
    if os.path.exists(local_tool):
        return f'"{local_tool}"'
    if os.name == 'nt':
        return f"{tool_name}.exe" 
    return tool_name

def clean_up_work_dir(work_dir):
    print("--- Cleaning up temporary files ---")
    junk_exts = ['.pl', '.pm', '.py', '.exe', '.bat', '.conf', '.sh', '.cds', '.block.rr.txt', '.fasta', '.index', '.cidx', '.db', '.dir', '.pag']
    for root, dirs, files in os.walk(work_dir, topdown=False):
        if 'ks' in root: continue 
        for name in files:
            if name.endswith('.zip'): continue 
            if any(name.endswith(ext) for ext in junk_exts) or name == 'block.txt':
                try: os.remove(os.path.join(root, name))
                except: pass
        for name in dirs:
            if name == 'ks': continue
            try: os.rmdir(os.path.join(root, name))
            except: pass

def normalize_fasta(input_files, output_path):
    print(f"--- Normalizing CDS files into: {output_path} ---")
    valid_ids = set()
    if os.path.exists(output_path): os.remove(output_path)
    with open(output_path, 'w', encoding='utf-8', newline='\n') as out_f:
        for file_path in input_files:
            if not os.path.exists(file_path): continue
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as in_f:
                for line in in_f:
                    line = line.strip()
                    if not line: continue
                    if line.startswith('>'):
                        raw_header = line[1:].strip()
                        seq_id = raw_header.split()[0].strip()
                        valid_ids.add(seq_id)
                        out_f.write(f">{seq_id}\n")
                    else:
                        out_f.write(f"{line}\n")
    print(f"Total Unique Sequences Normalized: {len(valid_ids)}")
    return valid_ids

def prepare_block_file(raw_block_path, final_block_path, valid_ids):
    print("--- Cleaning Block File based on Normalized IDs ---")
    valid_lines_count = 0
    with open(raw_block_path, 'r', encoding='utf-8-sig', errors='ignore') as infile, \
          open(final_block_path, 'w', encoding='utf-8', newline='\n') as outfile:
        for line in infile:
            line = line.strip()
            if not line: continue
            if line.startswith('#') or 'MAXIMUM' in line or 'GAP' in line or 'Alignment' in line: continue
            parts = line.split()
            found_genes = [word.strip() for word in parts if word.strip() in valid_ids]
            if len(found_genes) >= 2:
                outfile.write(f"{found_genes[0]}\t{found_genes[1]}\n")
                valid_lines_count += 1
    print(f"Block file prepared: {valid_lines_count} pairs ready.")
    if valid_lines_count == 0:
        raise ValueError(f"No valid gene pairs found! Please check data.")

# =========================================================
# 4. 核心业务逻辑
# =========================================================

def zu_ks_calculate_run_tools(c):
    if isinstance(c, dict): place = os.path.basename(c.get('file_path', ''))
    else: place = c

    if not os.path.exists(FILE_KEEP_DIR): os.makedirs(FILE_KEEP_DIR)
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    if not os.path.exists(work_dir): os.makedirs(work_dir)

    print(f"--- Running KaKs Calculation in: {work_dir} ---")

    # 1. 复制核心文件
    required_files = ['calculate.Ks.pl', 'SeqStatistics.pm', 'clustalw2.exe']
    print(f"--- Copying core files from {CURRENT_DIR} ---")
    for filename in required_files:
        src_path = os.path.join(CURRENT_DIR, filename)
        dst_path = os.path.join(work_dir, filename)
        if os.path.exists(src_path):
            shutil.copy(src_path, dst_path)
        else:
            if filename == 'clustalw2.exe':
                print(f"⚠️ Warning: {filename} not found in {CURRENT_DIR}. Assuming it is in PATH or not needed by Perl script direct call.")
            else:
                raise FileNotFoundError(f"Missing core script: {filename}. Please put it in {CURRENT_DIR}")

    # 2. 准备目录
    cds_dir = os.path.join(work_dir, 'cds')
    blk_dir = os.path.join(work_dir, 'blk')
    ks_dir = os.path.join(work_dir, 'ks') 
    combined_dir = os.path.join(work_dir, '1_2') 
    
    os.makedirs(cds_dir, exist_ok=True)
    os.makedirs(blk_dir, exist_ok=True)
    os.makedirs(ks_dir, exist_ok=True)
    os.makedirs(combined_dir, exist_ok=True)

    # 3. 清理旧索引
    for ext in ['*.index', '*.cidx', '*.db', '*.dir', '*.pag']:
        for dead_file in glob.glob(os.path.join(combined_dir, ext)):
            try: os.remove(dead_file)
            except: pass

    # 4. 处理 CDS
    cds1_path = os.path.join(cds_dir, '1.cds')
    cds2_path = os.path.join(cds_dir, '2.cds')
    if os.path.exists(os.path.join(work_dir, '1.cds')): shutil.move(os.path.join(work_dir, '1.cds'), cds1_path)
    if os.path.exists(os.path.join(work_dir, '2.cds')): shutil.move(os.path.join(work_dir, '2.cds'), cds2_path)
    combined_fasta_path = os.path.join(combined_dir, '1_2.fasta')
    valid_ids = normalize_fasta([cds1_path, cds2_path], combined_fasta_path)
    
    # 5. 处理 Block
    block_src = os.path.join(work_dir, 'block.txt')
    block_dst = os.path.join(blk_dir, '1_2.block.rr.txt')
    if os.path.exists(block_src): prepare_block_file(block_src, block_dst, valid_ids)
    else: raise FileNotFoundError("Block file not found!")

    # 6. 生成 Python 驱动脚本
    abs_blk_path = os.path.abspath(block_dst).replace('\\', '/')
    abs_fasta_path = os.path.abspath(combined_fasta_path).replace('\\', '/')
    abs_output_file = os.path.abspath(os.path.join(ks_dir, '1_2.ks.txt')).replace('\\', '/')
    run_cmd_script = os.path.join(work_dir, "run_direct.py")
    
    with open(run_cmd_script, 'w', encoding='utf-8') as f:
        f.write(f"""
import subprocess
import sys
import os

# 将当前目录加入 PATH (为了 clustalw2)
cwd = os.getcwd()
os.environ["PATH"] = cwd + os.pathsep + os.environ["PATH"]

# 构造命令
cmd = [
    "perl", 
    "calculate.Ks.pl", 
    "1_2", 
    "1", 
    r"{abs_blk_path}", 
    r"{abs_fasta_path}", 
    r"{abs_output_file}" 
]

print("Executing direct command: " + " ".join(cmd))
sys.stdout.flush()

# 执行 (注意：这里会继承 tools.py 传过来的 env，其中包含了 Perl 路径)
env = os.environ.copy()
ret = subprocess.call(cmd, env=env, shell=True)
sys.exit(ret)
""")

    # 7. 配置环境变量 (寻找并注入 Perl)
    env = os.environ.copy()
    current_path = env.get("PATH", "")
    
    # 查找嵌入式 Perl
    perl_bin_path = find_perl_path()
    
    # 构建新 PATH：Perl目录 + 当前工具目录 + 原有PATH
    new_path = CURRENT_DIR + os.pathsep + current_path
    if perl_bin_path:
        # 这里的 os.pathsep 在 Windows 上是分号 ;
        new_path = perl_bin_path + os.pathsep + new_path
    
    env["PATH"] = new_path

    # 8. 运行
    print(f"Executing: {PYTHON_EXE} run_direct.py")
    # 打印部分 Path 用于调试
    print(f"Using PATH prefix: {new_path[:200]}...") 

    result = subprocess.run([PYTHON_EXE, run_cmd_script], cwd=work_dir, env=env, capture_output=True)
    
    stdout_msg = safe_decode(result.stdout)
    stderr_msg = safe_decode(result.stderr)

    if stdout_msg: print("STDOUT:", stdout_msg)
    
    if result.returncode != 0:
        print("STDERR:", stderr_msg)
        # 更加友好的报错提示
        if "perl" in stderr_msg and ("不是内部" in stderr_msg or "not recognized" in stderr_msg):
            raise Exception(f"CRITICAL ERROR: Perl executable not found.\n1. Please install Strawberry Perl.\n2. Or update MANUAL_PERL_PATH in tools.py.\nOriginal Error: {stderr_msg}")
        else:
            raise Exception(f"Calculation Script Failed: {stderr_msg}")
    
    print("--- Calculation Finished Successfully ---")
    clean_up_work_dir(work_dir)
    return None