# Written by Yu Zijian
# E-main: yuzijian1010@163.com

import os
import sys
import glob
import time
import zipfile
import shutil
import traceback
import uuid
from urllib.parse import quote, unquote

from django.shortcuts import render
from django.http import HttpResponse, FileResponse 
from django.conf import settings # 引入settings以获取准确的根目录

# 引入邮件工具
try:
    from .tools_email import youjian
except ImportError:
    print("Warning: tools_email.py not found.")

try:
    from .tools import *
except Exception:
    print("Warning: tools.py definition not found or circular import.")
    traceback.print_exc()

# ==========================================
# 核心修正：使用 settings.BASE_DIR 获取项目根目录
# ==========================================
def get_real_base_dir():
    """直接从Django配置获取根目录，解决路径层级问题"""
    return str(settings.BASE_DIR)

path_get = get_real_base_dir()

# 确保根目录下的 file_keep 存在
required_dirs = ['file_keep']
for d in required_dirs:
    full_path = os.path.join(path_get, d)
    if not os.path.exists(full_path):
        os.makedirs(full_path)

print(f"✅ [View] 项目根目录: {path_get}")
print(f"✅ [View] file_keep 位置: {os.path.join(path_get, 'file_keep')}")


def name_set():
    """生成唯一的工作目录名"""
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    folder_path = os.path.join(path_get, 'file_keep', folder_name)
    from api.download_access import create_job_directory
    create_job_directory(folder_path)
    return folder_name

def keep_file(na, c):
    """保存单个上传文件"""
    if not na: return None
    # 路径修正：file_keep 在根目录
    target_dir = os.path.join(path_get, 'file_keep', c, 'orthomcl')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    file_path = os.path.join(target_dir, na.name)
    with open(file_path, 'wb+') as destination:
        for chunk in na.chunks():
            destination.write(chunk)
    return file_path

def keep_files(na, c):
    """保存多个上传文件"""
    if not na: return
    for f in na:
        keep_file(f, c)

def zip_file(request, place, files, target_email=None):
    """
    打包文件 -> 发送邮件(如果提供了email) -> 直接触发浏览器下载
    """
    # 路径修正：file_keep 在根目录
    target_dir = os.path.join(path_get, 'file_keep', place)
    zip_filename = 'GeneRetention_Result.zip' 
    zip_filepath = os.path.join(target_dir, zip_filename)

    file_list = []
    
    if '*' in files:
        search_pattern = os.path.join(target_dir, files.strip())
        file_list.extend(glob.glob(search_pattern))
    else:
        file_names = files.split()
        for fname in file_names:
            full_path = os.path.join(target_dir, fname)
            if os.path.exists(full_path):
                file_list.append(full_path)
            elif '*' in fname:
                 file_list.extend(glob.glob(os.path.join(target_dir, fname)))

    try:
        # 1. 压缩逻辑
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in file_list:
                if os.path.isdir(file_path):
                    for root, dirs, files_in_dir in os.walk(file_path):
                        for file in files_in_dir:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, start=os.path.dirname(file_path))
                            zf.write(full_path, arcname=arcname)
                else:
                    zf.write(file_path, arcname=os.path.basename(file_path))
        
        # 2. 邮件发送逻辑 (需确保 tools_email.py 已更新为接受 3 个参数)
        if target_email:
            print(f"准备发送邮件至: {target_email}")
            youjian(target_email, zip_filepath, place)

        # 3. 直接下载逻辑
        response = FileResponse(open(zip_filepath, 'rb'))
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        return response

    except Exception as e:
        print(f"Zip/Email Error: {e}")
        traceback.print_exc()
        return HttpResponse(f"Error processing request: {e}", status=500)

def file_download(request):
    try:
        file_path_encoded = request.GET.get('file', '')
        if not file_path_encoded:
            return HttpResponse("No file specified", status=400)
        file_path = unquote(file_path_encoded)
        if 'file_keep' not in file_path:
             return HttpResponse("Access Denied.", status=403)
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
        else:
            return HttpResponse(f"File not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {e}", status=500)


def zu_retention_run(request):
    """核心运行逻辑"""
    if request.method != 'POST':
        return render(request, 'zu_baoliu.html')

    try:
        mc_files = request.FILES.getlist("mc_file", None)
        if not mc_files:
            single_file = request.FILES.get("mc_file", None)
            if single_file:
                mc_files = [single_file]

        if not mc_files:
            return HttpResponse("Please upload files.", status=400)
        
        user_email = request.POST.get('email', '').strip()

        c = name_set()
        keep_files(na=mc_files, c=c)
        
        zu_retention_run_tools(place=c)
        
        files = "output"
        return zip_file(request, c, files, target_email=user_email)
        
    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Error during execution: {str(e)}")