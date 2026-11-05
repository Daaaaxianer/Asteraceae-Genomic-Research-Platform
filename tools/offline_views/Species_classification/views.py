# Written by Yu Zijian
# E-mail: yuzijian1010@163.com

import os
import subprocess
import sys
import time
import zipfile
import uuid
import traceback
from django.shortcuts import render
from django.http import HttpResponse, FileResponse

# 尝试导入业务逻辑模块
try:
    from . import tools
except ImportError:
    print("Warning: tools.py not found or circular import.")
    tools = None

# =========================================================
# 1. 基础路径配置 (严格按照要求指定绝对路径)
# =========================================================

BASE_PROJECT_PATH = "/wangjp/Asteraceae/Asteraceae"
FILE_KEEP_DIR = os.path.join(BASE_PROJECT_PATH, 'file_keep')
RUNNER_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'runner.py')
RUNNER_TIMEOUT_SECONDS = 120

# 确保必要文件夹存在
if not os.path.exists(FILE_KEEP_DIR):
    try:
        os.makedirs(FILE_KEEP_DIR)
        print(f"✅ Created directory: {FILE_KEEP_DIR}")
    except Exception as e:
        print(f"❌ Error creating directory: {e}")

print(f"✅ [View] 文件存储区: {FILE_KEEP_DIR}")


# =========================================================
# 2. 辅助工具函数
# =========================================================

def name_set():
    """生成唯一的工作目录名 (时间戳_随机码)"""
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    folder_path = os.path.join(FILE_KEEP_DIR, folder_name)
    from api.download_access import create_job_directory
    create_job_directory(folder_path)
    return folder_name

def keep_file(na, c):
    """保存单个上传文件"""
    if not na: return None
    target_dir = os.path.join(FILE_KEEP_DIR, c)
    file_path = os.path.join(target_dir, na.name)
    with open(file_path, 'wb+') as destination:
        for chunk in na.chunks():
            destination.write(chunk)
    return file_path

def write_species_classification_error_artifacts(place, message, details=""):
    target_dir = os.path.join(FILE_KEEP_DIR, place)
    taxonomy_path = os.path.join(target_dir, 'taxonomy_results.txt')
    error_log_path = os.path.join(target_dir, 'error_log.txt')

    if not os.path.exists(taxonomy_path):
        with open(taxonomy_path, 'w', encoding='utf-8') as taxonomy_file:
            taxonomy_file.write("Species Name\tNCBI TaxID\tLineage\n")
            taxonomy_file.write(f"Task\tError: {message}\n")

    with open(error_log_path, 'w', encoding='utf-8') as error_log:
        error_log.write(message)
        if details:
            error_log.write("\n\n")
            error_log.write(details)

def run_species_classification_job(place):
    command = [sys.executable, RUNNER_SCRIPT_PATH, place, FILE_KEEP_DIR]

    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=RUNNER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        timeout_output = e.stdout or ""
        write_species_classification_error_artifacts(
            place,
            f"Species classification timed out after {RUNNER_TIMEOUT_SECONDS} seconds.",
            timeout_output,
        )
        return
    except Exception as e:
        write_species_classification_error_artifacts(
            place,
            f"Species classification runner failed to start: {e}",
            traceback.format_exc(),
        )
        return

    if completed.returncode != 0:
        write_species_classification_error_artifacts(
            place,
            f"Species classification runner exited with code {completed.returncode}.",
            completed.stdout or "",
        )

def zip_and_return_stream(place):
    """
    打包结果文件夹中的内容并直接返回文件流（直接下载，不跳转页面）
    """
    target_dir = os.path.join(FILE_KEEP_DIR, place)
    zip_filename = 'result.zip'
    zip_filepath = os.path.join(target_dir, zip_filename)

    # 获取所有非 zip 文件进行压缩
    files_to_zip = []
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            # 排除生成的 zip 本身
            if file == zip_filename:
                continue
            files_to_zip.append(os.path.join(root, file))

    try:
        # 创建压缩包
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in files_to_zip:
                # 在 zip 内保持相对路径 (扁平化)
                arcname = os.path.relpath(file_path, target_dir)
                zf.write(file_path, arcname=arcname)
        
        # 直接返回文件流
        if os.path.exists(zip_filepath):
            # 打开文件流，Django 会自动处理关闭
            response = FileResponse(open(zip_filepath, 'rb'), as_attachment=True)
            # 设置下载文件名
            response['Content-Disposition'] = f'attachment; filename="Species_Classification_Result.zip"'
            return response
        else:
            return HttpResponse("Error: Zip file generation failed.", status=500)

    except Exception as e:
        print(f"Zip Error: {e}")
        traceback.print_exc()
        return HttpResponse(f"Server Error during packaging: {e}", status=500)


# =========================================================
# 3. 视图函数
# =========================================================

def species_classification(request):
    """渲染首页"""
    return render(request, 'species_classification.html')

def species_classification_run(request):
    """处理表单提交与运行逻辑"""
    try:
        # 1. 获取上传的文件
        file1 = request.FILES.get("file1", None)
        if file1 is None:
            return HttpResponse("Please upload a file!", status=400)

        # 2. 创建唯一工作目录
        c = name_set()
        
        # 3. 重命名并保存文件
        file1.name = "sp_list.txt"
        keep_file(na=file1, c=c)
        
        # 4. 调用 tools 中的业务逻辑
        if True:
            # 关键：传入绝对路径 FILE_KEEP_DIR
            run_species_classification_job(c)
        else:
            return HttpResponse("Error: Backend tools module not loaded.", status=500)

        # 5. 打包并直接下载
        return zip_and_return_stream(c)

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Server Error: {e}", status=500)
