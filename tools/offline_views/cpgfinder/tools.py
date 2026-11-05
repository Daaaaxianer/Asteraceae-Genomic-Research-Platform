import os
import random
import string
import subprocess
import zipfile
from django.conf import settings

# ================= 核心路径配置 =================

# 1. 获取当前 tools.py 所在的绝对路径
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 向前回溯 3 层，回到项目根目录 (根据你的项目结构调整)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_SCRIPT_DIR)))

# 3. 拼接 file_keep 路径
FILE_KEEP_DIR = os.path.join(PROJECT_ROOT, 'file_keep')

# ==========================================================

# Cpgfinder 可执行文件名 (确保该文件在服务器上有 +x 权限)
CPGFINDER_EXEC = '/www/tools/soft_tools/cpgfinder' 

def name_set():
    """
    在 file_keep 中创建一个随机命名的文件夹，返回文件夹名
    """
    # 确保 file_keep 主目录存在
    if not os.path.exists(FILE_KEEP_DIR):
        try:
            os.makedirs(FILE_KEEP_DIR)
        except PermissionError:
            raise Exception(f"Permission error: could not create directory {FILE_KEEP_DIR}. Please check the directory permissions.")

    while True:
        c = ''.join(random.sample(string.digits, 9))
        target_dir = os.path.join(FILE_KEEP_DIR, c)
        if not os.path.exists(target_dir):
            from api.download_access import create_job_directory
            create_job_directory(target_dir)
            return c

def keep_file(file_obj, folder_name):
    """
    保存并深度清洗 FASTA 文件
    改进点：自动简化复杂的 Header，防止工具崩溃
    """
    destination_dir = os.path.join(FILE_KEEP_DIR, folder_name)
    
    # 1. 清理文件名
    clean_name = file_obj.name.replace(" ", "_")
    destination_path = os.path.join(destination_dir, clean_name)
    
    # 2. 读取并解码
    try:
        content = file_obj.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            file_obj.seek(0)
            content = file_obj.read().decode('latin-1')
        except Exception:
            raise Exception("File encoding error: please upload a standard FASTA text file.")

    # 3. 深度清洗 (Header 简化 + 序列过滤)
    lines = content.splitlines()
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith(">"):
            # 【关键修改】：只保留 Header 的第一部分（空格前的内容）
            # 例如：">id1 description" -> ">id1"
            # 这一步能解决 99% 因标题过长或含特殊字符导致的崩溃
            simple_header = line.split()[0]
            
            # 如果 ID 还是很长或包含 |，进一步处理（可选，视工具敏感度而定）
            # 这里将 | 替换为 _ 以防万一
            simple_header = simple_header.replace("|", "_")
            
            cleaned_lines.append(simple_header)
        else:
            # 序列行：只保留 ACGT 字母并转大写
            seq_content = ''.join(filter(str.isalpha, line)).upper()
            if seq_content:
                cleaned_lines.append(seq_content)
    
    # 4. 写入文件 (确保使用 Linux 换行符)
    final_content = "\n".join(cleaned_lines) + "\n"

    with open(destination_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(final_content)
            
    return clean_name

def run_cpgfinder_process(place, island, cg_percent, gc_ratio, filename):
    """
    使用 subprocess 调用 cpgfinder
    """
    # 组合完整的工作目录路径
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    output_file_path = os.path.join(work_dir, 'cpgfinder_result.txt')
    
    # 确保 filename 只是文件名，不包含路径
    filename_only = os.path.basename(filename)
    
    # 构建命令列表 (将所有参数转为 str)
    cmd = [
        CPGFINDER_EXEC,
        '-f', str(filename_only),
        '-l', str(island),
        '-p', str(cg_percent),
        '-r', str(gc_ratio)
    ]
    
    try:
        with open(output_file_path, 'w') as outfile:
            # subprocess.run 替代 os.system
            result = subprocess.run(
                cmd,
                cwd=work_dir,           # 关键：指定在随机子目录下运行
                stdout=outfile,         # 标准输出重定向到文件
                stderr=subprocess.PIPE, # 捕获错误输出
                text=True,              # 以文本模式处理
                timeout=600             # 设置10分钟超时
            )
            
        # 检查返回值
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error occurred."
            if "sequence" in error_msg.lower():
                raise Exception(f"The tool could not read the sequence. Check the FASTA format. Internal error: {error_msg}")
            else:
                raise Exception(f"Cpgfinder failed (code {result.returncode}): {error_msg}")
            
        # 检查结果文件是否生成且不为空
        # 注意：某些情况下如果没有 CpG 岛，文件可能是空的，视具体业务逻辑决定是否报错
        # 这里保留原逻辑，报错提示
        if not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
             # 可以尝试写入一个 "No CpG Islands found" 到结果文件，避免用户以为出错了
             # 这里保持原有报错逻辑
             raise Exception("The analysis finished with an empty result file. No CpG islands may have been predicted for this sequence.")

    except FileNotFoundError:
        raise Exception(f"Command not found: '{CPGFINDER_EXEC}'. Please check the configured path.")
    except subprocess.TimeoutExpired:
        raise Exception("Analysis timed out after 10 minutes. The file may be too large.")
    except Exception as e:
        raise Exception(f"The tool failed: {str(e)}")

def create_zip_archive(place, target_filename):
    """
    使用 Python 原生 zipfile 模块打包
    """
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    source_file = os.path.join(work_dir, target_filename)
    zip_file_path = os.path.join(work_dir, 'result.zip')
    
    if not os.path.exists(source_file):
        return None
        
    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # arcname=target_filename 确保压缩包解压后直接是文件名，不带长路径
            zf.write(source_file, arcname=target_filename)
        return zip_file_path
    except Exception as e:
        print(f"Zip creation failed: {e}")
        return None