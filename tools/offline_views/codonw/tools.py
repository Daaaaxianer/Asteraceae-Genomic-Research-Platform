import os
import random
import string
import subprocess
import zipfile

# ================= 配置区域 =================
# Linux 服务器路径配置
BASE_FILE_KEEP_PATH = "/wangjp/Asteraceae/Asteraceae/file_keep"
# 指向编译好的可执行文件 (确保已执行 chmod +x)
CODONW_EXE_PATH = "/www/tools/codonW/codonw" 
# ===========================================

def name_set():
    """生成随机文件夹ID"""
    c = ''.join(random.choices(string.ascii_letters + string.digits, k=9))
    folder_path = os.path.join(BASE_FILE_KEEP_PATH, c)
    from api.download_access import create_job_directory
    create_job_directory(folder_path)
    return c

def save_uploaded_file(file_obj, folder_id, target_name="1.fasta"):
    """
    保存并【清洗】上传的文件。
    """
    destination_path = os.path.join(BASE_FILE_KEEP_PATH, folder_id, target_name)
    
    content = ""
    # 读取文件内容并解码为字符串
    try:
        # 尝试直接读取文本
        content = file_obj.read().decode('utf-8', errors='ignore')
    except Exception:
        # 如果读取失败，重置指针再次尝试
        try:
            file_obj.seek(0)
            content = file_obj.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"File Read Error: {e}")
            return

    with open(destination_path, 'w', encoding='utf-8') as f:
        # 确保 content 不为空
        if not content:
            return

        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue # 跳过空行
            
            if line.startswith(">"):
                # 【重要清洗步骤】
                # 1. 以空格分割，只取第一部分 (去掉 gene=... 等描述)
                # 2. 限制长度为 50 字符
                clean_header = line.split()[0][:50]
                f.write(clean_header + "\n")
            else:
                # 序列行直接写入（转大写防止 codonw 不识别小写）
                f.write(line.upper() + "\n")

def codonw_run_tools(folder_id, output_prefix):
    """
    运行 CodonW 分析 (Linux 版)
    """
    # 1. 获取各个路径的绝对地址
    work_dir = os.path.join(BASE_FILE_KEEP_PATH, folder_id)
    exe_dir = os.path.dirname(CODONW_EXE_PATH)  # 获取 CodonW 所在的文件夹
    
    # 2. 构造输入输出文件的【绝对路径】
    input_abs_path = os.path.join(work_dir, "1.fasta")
    output_abs_path = os.path.join(work_dir, f"{output_prefix}.out")
    blk_abs_path = os.path.join(work_dir, f"{output_prefix}.blk")

    # 3. 检查输入文件是否存在
    if not os.path.exists(input_abs_path):
        print(f"Error: Input file not found at {input_abs_path}")
        return
        
    # 3.1 检查 CodonW 是否有执行权限 (Linux 特有检查)
    if not os.access(CODONW_EXE_PATH, os.X_OK):
        print(f"Permission Error: {CODONW_EXE_PATH} is not executable.")
        print("Please run: chmod +x " + CODONW_EXE_PATH)
        return

    # 4. 构建命令
    command = [
        CODONW_EXE_PATH,
        input_abs_path,
        output_abs_path,
        blk_abs_path,
        "-nomenu",
        "-nowarn",
        "-all_indices"  
    ]
    
    print(f"--- Starting CodonW for folder {folder_id} ---")
    try:
        # 运行命令，cwd=exe_dir 确保能找到 codon.dat 等配置文件
        result = subprocess.run(
            command, 
            cwd=exe_dir,
            check=False, 
            capture_output=True, 
            timeout=120
        )
        
        # 打印输出以便调试
        if result.returncode != 0:
            print(f"CodonW Process Returned Error Code: {result.returncode}")
        
        stdout_msg = result.stdout.decode(errors='ignore').strip()
        stderr_msg = result.stderr.decode(errors='ignore').strip()
        
        if stdout_msg: print(f"STDOUT: {stdout_msg}")
        if stderr_msg: print(f"STDERR: {stderr_msg}")

        # 检查是否生成了文件
        if os.path.exists(output_abs_path) and os.path.getsize(output_abs_path) > 0:
            print("Success: Output file generated.")
        else:
            print("Failure: Output file is missing or empty.")

    except subprocess.TimeoutExpired:
        print("Error: CodonW execution timed out (over 120s).")
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")

def zip_results(folder_id, file_list_str):
    """
    压缩结果文件
    """
    work_dir = os.path.join(BASE_FILE_KEEP_PATH, folder_id)
    zip_name = "CodonW_Result.zip"
    zip_path = os.path.join(work_dir, zip_name)
    
    # 将文件名字符串转换为列表
    file_names = file_list_str.split() 
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files_found = False
            for file in file_names:
                file_abs_path = os.path.join(work_dir, file)
                if os.path.exists(file_abs_path):
                    # arcname 确保压缩包内不包含绝对路径，只包含文件名
                    zipf.write(file_abs_path, arcname=file)
                    files_found = True
            
            # 如果没找到任何文件
            if not files_found:
                print("Zip Error: No files found to compress.")
                return None
                
        if os.path.exists(zip_path):
            return zip_path
            
    except Exception as e:
        print(f"Zip Error: {str(e)}")
        
    return None