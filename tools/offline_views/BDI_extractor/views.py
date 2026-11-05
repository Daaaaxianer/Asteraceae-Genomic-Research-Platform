# Written by Yu Zijian
# E-main: yuzijian1010@163.com

import os
import sys
import glob
import time
import uuid
import zipfile
import traceback
from urllib.parse import quote, unquote

from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings

# =========================================================
# 导入业务逻辑 (tools.py)
# 确保 tools.py 位于与 views.py 同级目录下
# =========================================================
try:
    from .tools import *
except ImportError:
    print("❌ Critical Error: 'tools.py' definition not found or circular import.")
    traceback.print_exc()

# =========================================================
# 路径配置
# =========================================================
def get_real_base_dir():
    """自动判断运行环境，返回正确的根目录"""
    # 假设结构为: ProjectRoot/tools/views.py
    # os.path.abspath(__file__) -> .../ProjectRoot/tools/views.py
    # dirname -> .../ProjectRoot/tools
    # dirname -> .../ProjectRoot
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 全局变量：当前工作根目录
path_get = get_real_base_dir()

# 确保必要文件夹存在
required_dirs = ['file_keep', os.path.join('file_keep', 'species_data')]
for d in required_dirs:
    full_path = os.path.join(path_get, d)
    if not os.path.exists(full_path):
        os.makedirs(full_path)

print(f"✅ [View] Current Working Directory: {path_get}")


# =========================================================
# 辅助函数
# =========================================================

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
    target_dir = os.path.join(path_get, 'file_keep', c)
    file_path = os.path.join(target_dir, na.name)
    # 使用 chunk 写入，防止大文件占用过多内存
    with open(file_path, 'wb+') as destination:
        for chunk in na.chunks():
            destination.write(chunk)
    return file_path

def keep_files(na, c):
    """保存多个上传文件"""
    if not na: return
    for f in na:
        keep_file(f, c)

def zip_file(request, place, files):
    """
    压缩文件并返回下载页面
    """
    target_dir = os.path.join(path_get, 'file_keep', place)
    zip_filename = 'result.zip'
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
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in file_list:
                # arcname 确保压缩包内不包含绝对路径
                zf.write(file_path, arcname=os.path.basename(file_path))
    except Exception as e:
        print(f"Zip Error: {e}")
        traceback.print_exc()

    # 生成下载链接
    download_link = f'/tools/download/?file={quote(zip_filepath)}'
    return render(request, 'successful.html', {'download_link': download_link})

def file_download(request):
    """
    通用下载视图
    """
    try:
        file_path_encoded = request.GET.get('file', '')
        if not file_path_encoded:
            return HttpResponse("No file specified", status=400)
        
        file_path = unquote(file_path_encoded)
        
        # 安全检查：只允许下载 file_keep 或 database 下的文件
        if 'file_keep' not in file_path and 'database' not in file_path:
             return HttpResponse("Access Denied: File must be in authorized directory.", status=403)
        
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
        else:
            return HttpResponse(f"File not found on server: {file_path}", status=404)
    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Download Error: {e}", status=500)


# =========================================================
# 业务视图函数
# =========================================================

def extract_row(request):
    """渲染提取页面"""
    return render(request, 'extract_row.html')

def extract_column_run(request):
    """处理提取逻辑"""
    try:
        row = request.FILES.get("row", None)
        row_num = request.POST.get("row_num", None)
        
        if row is None:
            return render(request, 'extract_row.html')
        
        # 1. 创建工作目录
        c = name_set()
        
        # 2. 更健壮的文件名处理 (修复了 split('.') 的潜在 bug)
        filename_base, filename_ext = os.path.splitext(row.name)
        row_name = filename_base
        row_last = filename_ext.replace('.', '') # 去除点号，例如 .txt -> txt
        
        # 3. 保存文件
        keep_file(na=row, c=c)
        
        # 4. 调用逻辑脚本 (确保 tools.py 中有这个函数)
        if 'extr_row_run' in globals():
            print(f"Running extr_row_run in {c}...")
            extr_row_run(place=c, row_num=row_num, row_name=row_name, row_last=row_last)
        else:
            return HttpResponse("Error: Function 'extr_row_run' not found in tools.py")

        # 5. 打包结果
        files = f'{row_name}.new.{row_last}'
        return zip_file(request, c, files)
        
    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Error during execution: {str(e)}")
