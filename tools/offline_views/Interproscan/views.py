import os
import random
import string
import subprocess
import zipfile
import time
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.urls import reverse

# ================= 配置区域 =================

# 1. 临时文件存储根目录
FILE_KEEP_ROOT = '/wangjp/Asteraceae/Asteraceae/file_keep'

# 2. Interproscan 可执行文件绝对路径
INTERPROSCAN_EXEC = "/bio/yzj/tools/Interproscan/interproscan-5.62-94.0/interproscan.sh"

# 3. 环境变量路径
JAVA_BIN_PATH = "/bio/yzj/tools/Java_18/jdk-18.0.2.1/bin"
PYTHON_BIN_PATH = "/usr/local/bin" 
SYSTEM_BIN_PATH = "/usr/bin:/bin"

# 自动创建存储目录
if not os.path.exists(FILE_KEEP_ROOT):
    try:
        os.makedirs(FILE_KEEP_ROOT, exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create {FILE_KEEP_ROOT}")

# ================= 工具函数 (Tools) =================

def get_random_dir_name():
    from api.download_access import create_job_directory
    while True:
        dir_name = ''.join(random.sample(string.digits, 9))
        try:
            create_job_directory(os.path.join(FILE_KEEP_ROOT, dir_name))
            return dir_name
        except FileExistsError:
            continue

def save_uploaded_file(file_obj, dir_code):
    target_dir = os.path.join(FILE_KEEP_ROOT, dir_code)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    file_path = os.path.join(target_dir, "result.fasta")
    with open(file_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    return file_path

# ================= 核心逻辑：后台启动任务 =================

def run_interproscan_background(dir_code):
    """
    使用 Popen 启动后台任务，不等待完成，立刻返回
    解决 502 Bad Gateway 问题
    """
    work_dir = os.path.join(FILE_KEEP_ROOT, dir_code)
    
    # 1. 构建环境变量
    env = os.environ.copy()
    env['PATH'] = f"{JAVA_BIN_PATH}:{PYTHON_BIN_PATH}:{SYSTEM_BIN_PATH}:{env.get('PATH', '')}"
    
    # 2. 构造命令
    # 注意：-b result 表示输出文件前缀为 result
    cmd = f"{INTERPROSCAN_EXEC} -i result.fasta -b result -goterms -iprlookup -pa -dp -f tsv,xml,gff3 -cpu 8"
    
    # 3. 准备日志文件 (用于重定向输出，不阻塞主进程)
    stdout_log = open(os.path.join(work_dir, "run.stdout"), "w")
    stderr_log = open(os.path.join(work_dir, "run.stderr"), "w")

    # 4. 启动进程 (关键：close_fds=True 允许 Django 进程断开连接)
    try:
        subprocess.Popen(
            cmd,
            cwd=work_dir,
            shell=True,
            env=env,
            stdout=stdout_log,
            stderr=stderr_log,
            executable='/bin/bash',
            close_fds=True
        )
    except Exception as e:
        # 如果启动都失败了，记录一下
        with open(os.path.join(work_dir, "start_error.txt"), "w") as f:
            f.write(str(e))

# ================= 视图函数 (Views) =================

def interproscan(request):
    """渲染提交页面"""
    return render(request, 'interproscan.html')

def tools(request):
    return render(request, 'tools.html')

def interproscan_run(request):
    """
    步骤1: 接收文件 -> 启动后台任务 -> 重定向到等待页面
    """
    if request.method == 'POST':
        my_file = request.FILES.get('file1', None)
        
        if my_file is None:
            return render(request, 'interproscan.html', {'error': 'No file uploaded.'})
            
        # 限制大小 10MB
        if my_file.size > 10 * 1024 * 1024:
            return render(request, 'interproscan.html', {'error': 'File size exceeds the limit (10MB).'})

        # 1. 保存文件
        dir_code = get_random_dir_name()
        save_uploaded_file(my_file, dir_code)

        # 2. 启动后台任务 (瞬间完成，不会卡顿)
        run_interproscan_background(dir_code)

        # 3. 重定向到状态检查页面 (带上 job_id)
        # 【关键修复】自动检测是否需要 'tools:' 前缀
        try:
            # 优先尝试带命名空间的 URL (针对您报错中显示的 /tools/ 路径)
            base_url = reverse('tools:interproscan_result')
        except:
            # 如果失败，尝试默认 URL
            base_url = reverse('interproscan_result')
            
        return redirect(f'{base_url}?job_id={dir_code}')

    return redirect('interproscan')

def interproscan_result(request):
    """
    步骤2: 状态轮询页面
    """
    job_id = request.GET.get('job_id')
    if not job_id:
        return redirect('interproscan')
        
    work_dir = os.path.join(FILE_KEEP_ROOT, job_id)
    
    # 判断任务完成标准：检查结果文件是否存在
    result_file = os.path.join(work_dir, "result.tsv")
    is_finished = os.path.exists(result_file)
    
    return render(request, 'interproscan_result.html', {
        'job_id': job_id,
        'finished': is_finished
    })

def interproscan_download(request):
    """
    步骤3: 结果打包下载
    """
    job_id = request.GET.get('job_id')
    if not job_id:
        return HttpResponse("No Job ID provided.")

    work_dir = os.path.join(FILE_KEEP_ROOT, job_id)
    zip_filename = "result.zip"
    zip_file_path = os.path.join(work_dir, zip_filename)
    
    # 如果 Zip 不存在，则创建
    if not os.path.exists(zip_file_path):
        files_to_zip = ['result.tsv', 'result.xml', 'result.gff3', 'run.stderr', 'run.stdout']
        try:
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                files_found = False
                for fname in files_to_zip:
                    fpath = os.path.join(work_dir, fname)
                    if os.path.exists(fpath):
                        zipf.write(fpath, arcname=fname)
                        files_found = True
                
                if not files_found:
                    # 如果空结果，写入说明
                    dummy_path = os.path.join(work_dir, "readme.txt")
                    with open(dummy_path, 'w') as f:
                        f.write("No result files generated. Please check run.stderr log.")
                    zipf.write(dummy_path, arcname="README.txt")
                    
        except Exception as e:
            return HttpResponse(f"Error packing zip: {str(e)}")
    
    return FileResponse(open(zip_file_path, 'rb'), as_attachment=True, filename='interproscan_result.zip')