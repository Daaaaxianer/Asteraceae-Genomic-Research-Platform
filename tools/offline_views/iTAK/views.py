import os
import glob
import shutil
import random
import re
import string
import subprocess
import zipfile
import concurrent.futures
import traceback
from urllib.parse import unquote
from django.shortcuts import render
from django.http import HttpResponse, FileResponse, HttpResponseRedirect

# ==========================================
# 1. 全局配置区域
# ==========================================

# 指定文件存储的绝对路径根目录
FILE_KEEP_DIR = '/wangjp/Asteraceae/Asteraceae/file_keep'

# 【关键修改】iTAK.pl 的绝对路径 (根据您提供的信息)
ITAK_EXECUTABLE = '/bio/yzj/tools/iTAK-1.7a/iTAK.pl'
SAFE_FILENAME_RE = re.compile(r'[^A-Za-z0-9._-]+')

# ==========================================
# 2. 工具函数 (业务逻辑)
# ==========================================

def name_set():
    """
    生成唯一的随机任务ID
    """
    c = ''.join(random.sample(string.digits, 9))
    full_path = os.path.join(FILE_KEEP_DIR, c)
    
    while os.path.exists(full_path):
        c = ''.join(random.sample(string.digits, 9))
        full_path = os.path.join(FILE_KEEP_DIR, c)
        
    from api.download_access import create_job_directory
    create_job_directory(full_path)
    return c

def keep_files(files, c):
    """
    保存上传文件
    """
    save_dir = os.path.join(FILE_KEEP_DIR, c, 'orthomcl')
    os.makedirs(save_dir, exist_ok=True)

    for f in files:
        file_name = os.path.basename(f.name)
        safe_name = SAFE_FILENAME_RE.sub('_', file_name).strip('._')
        if not safe_name:
            safe_name = 'input.fasta'

        base_name, ext = os.path.splitext(safe_name)
        if not ext:
            ext = '.fasta'

        candidate_name = f"{base_name}{ext}"
        suffix = 1
        destination_path = os.path.join(save_dir, candidate_name)

        while os.path.exists(destination_path):
            candidate_name = f"{base_name}_{suffix}{ext}"
            destination_path = os.path.join(save_dir, candidate_name)
            suffix += 1

        with open(destination_path, 'wb') as destination_file:
            for chunk in f.chunks():
                destination_file.write(chunk)
    
    print(f"[DEBUG] Files saved to: {save_dir}")

def run_itak_single_process(file_path, work_dir):
    """
    运行 iTAK.pl (修复版：使用绝对路径)
    """
    file_abs_path = os.path.abspath(file_path)
    file_name = os.path.basename(file_path)
    
    # 1. 检查可执行文件是否存在
    if not os.path.exists(ITAK_EXECUTABLE):
        msg = f"[CRITICAL ERROR] iTAK executable NOT found at: {ITAK_EXECUTABLE}"
        print(msg)
        # 生成一个错误文件告知用户
        with open(os.path.join(work_dir, "SYSTEM_CONFIG_ERROR.txt"), "w") as f:
            f.write(msg)
        return

    # 2. 构建命令 (使用绝对路径)
    cmd = [ITAK_EXECUTABLE, file_abs_path]
    
    # 定义日志文件
    stdout_file = os.path.join(work_dir, f"{file_name}.stdout.txt")
    stderr_file = os.path.join(work_dir, f"{file_name}.stderr.txt")
    
    print(f"[DEBUG] Executing: {' '.join(cmd)}")
    env = os.environ.copy()
    path_parts = env.get('PATH', '').split(':') if env.get('PATH') else []
    required_paths = ['/usr/local/bin', '/usr/bin', '/bin']
    missing_paths = [path for path in required_paths if path not in path_parts]
    env['PATH'] = ':'.join(missing_paths + path_parts) if path_parts else ':'.join(required_paths)
    
    try:
        # 3. 执行命令并捕获所有输出
        result = subprocess.run(
            cmd, 
            cwd=work_dir, 
            capture_output=True, 
            text=True,
            env=env
        )
        
        # 4. 保存标准输出 (如果 iTAK 成功，结果可能在这里)
        if result.stdout:
            with open(stdout_file, "w") as f_out:
                f_out.write(result.stdout)
        else:
            with open(stdout_file, "w") as f_out:
                f_out.write("") # 创建空文件标记

        # 5. 保存错误日志 (如果 iTAK 失败，原因在这里)
        if result.stderr:
            with open(stderr_file, "w") as f_err:
                f_err.write(result.stderr)
            print(f"[WARNING] stderr captured for {file_name}")

        # 6. 检查返回值
        if result.returncode != 0:
            print(f"[ERROR] iTAK failed with return code: {result.returncode}")
            with open(os.path.join(work_dir, f"{file_name}_FAILED_CODE_{result.returncode}.txt"), "w") as f:
                f.write(f"Return Code: {result.returncode}\nCheck .stderr.txt for details.")
        else:
            print(f"[DEBUG] iTAK finished successfully (Exit Code 0).")

    except Exception as e:
        print(f"[CRITICAL] Python execution crashed for {file_path}: {e}")
        with open(os.path.join(work_dir, "PYTHON_CRASH_LOG.txt"), "w") as f:
            f.write(str(e))
            f.write("\n")
            f.write(traceback.format_exc())

def iTAK_run_tools(place):
    """
    核心逻辑：运行 -> 移动结果
    """
    job_dir = os.path.join(FILE_KEEP_DIR, place)
    orthomcl_dir = os.path.join(job_dir, 'orthomcl')
    output_dir = os.path.join(job_dir, 'output')
    
    os.makedirs(output_dir, exist_ok=True)

    # 1. 寻找输入文件
    target_files = []
    extensions = ['*.pep', '*.fasta', '*.fa', '*.txt']
    for ext in extensions:
        target_files.extend(glob.glob(os.path.join(orthomcl_dir, ext)))
    
    print(f"[DEBUG] Found {len(target_files)} input files to process.")

    # 2. 并行运行
    if target_files:
        with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run_itak_single_process, fp, job_dir) for fp in target_files]
            concurrent.futures.wait(futures)
    else:
        print("[WARNING] No input files found to run iTAK.")

    # 3. 移动结果 (全量扫描)
    print(f"[DEBUG] Moving results to {output_dir}...")
    
    exclude_names = ['orthomcl', 'output', '__MACOSX', 'result.zip']
    
    # 策略 A：扫描 job_dir 根目录
    for item in os.listdir(job_dir):
        if item in exclude_names:
            continue
            
        src_path = os.path.join(job_dir, item)
        dst_path = os.path.join(output_dir, item)
        
        try:
            if os.path.exists(src_path):
                shutil.move(src_path, dst_path)
                print(f"[DEBUG] Moved from root: {item}")
        except Exception as e:
            print(f"[ERROR] Failed to move {item}: {e}")
    
    # 策略 B：扫描 orthomcl 目录
    input_filenames = [os.path.basename(f) for f in target_files]
    
    for item in os.listdir(orthomcl_dir):
        if item in input_filenames: 
            continue 
            
        src_path = os.path.join(orthomcl_dir, item)
        dst_path = os.path.join(output_dir, item)
        
        if os.path.exists(src_path):
            try:
                if os.path.exists(dst_path):
                    base, ext = os.path.splitext(item)
                    dst_path = os.path.join(output_dir, f"{base}_extra{ext}")
                
                shutil.move(src_path, dst_path)
                print(f"[DEBUG] Moved from orthomcl: {item}")
            except Exception as e:
                print(f"[ERROR] Failed to move inner {item}: {e}")

def zip_results_python(place):
    """
    使用 Python zipfile 模块压缩
    """
    job_dir = os.path.join(FILE_KEEP_DIR, place)
    output_dir = os.path.join(job_dir, 'output')
    zip_file_path = os.path.join(job_dir, 'result.zip')
    
    print(f"[DEBUG] Zipping folder: {output_dir}")

    # 检查 output 是否为空
    if not os.path.exists(output_dir) or not os.listdir(output_dir):
        print("[WARNING] Output directory is EMPTY.")
        with open(os.path.join(output_dir, 'README_NO_RESULT.txt'), 'w') as f:
            f.write("No result files were generated.\n")
            f.write("Please check the .stderr.txt log files inside the zip for error details.")

    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, output_dir)
                    zipf.write(abs_path, rel_path)
        
        print(f"[DEBUG] Zip created successfully at: {zip_file_path}")
        return zip_file_path
    except Exception as e:
        print(f"[ERROR] Zip generation failed: {e}")
        return None

# ==========================================
# 3. Django Views
# ==========================================

def iTAK(request):
    return render(request, 'iTAK.html')

def iTAK_run(request):
    """
    主处理视图
    """
    if request.method != 'POST':
        return HttpResponseRedirect('/iTAK')

    files = request.FILES.getlist("file", None)
    
    if not files:
        return render(request, 'iTAK.html', {'error_msg': 'No files uploaded.'})
    
    c = "Unknown"
    try:
        # 1. Setup
        c = name_set()
        print(f"--- Starting Analysis Job: {c} ---")

        # 2. Save
        keep_files(files, c)
        
        # 3. Run
        iTAK_run_tools(c)
        
        # 4. Zip
        zip_path = zip_results_python(c)
        
        # 5. Download
        if zip_path and os.path.exists(zip_path):
            response = FileResponse(open(zip_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="iTAK_result_{c}.zip"'
            print(f"--- Job {c} Completed Successfully ---")
            return response
        else:
            return HttpResponse(f"Analysis finished but ZIP failed. Job ID: {c}", status=500)

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"[CRITICAL ERROR] Job {c} failed:\n{error_details}")
        return HttpResponse(f"Server Error. Job ID: {c}", status=500)

def download_file_view(request):
    """
    通用下载接口
    """
    file_path_param = unquote(request.GET.get('file', ''))
    
    abs_path = os.path.abspath(file_path_param)
    if not abs_path.startswith(FILE_KEEP_DIR):
        return HttpResponse("Access Denied", status=403)

    if os.path.exists(abs_path) and os.path.isfile(abs_path):
        response = FileResponse(open(abs_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(abs_path)}"'
        return response
    else:
        return HttpResponse("File not found", status=404)
