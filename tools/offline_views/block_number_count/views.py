#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import time
import uuid
import zipfile
import io
import glob
import traceback
from urllib.parse import quote, unquote

from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings

# 引入同目录下的工具函数
try:
    from . import tools
except ImportError:
    import tools

# =========================================================
# 基础配置
# =========================================================
BASE_DIR = str(settings.BASE_DIR)
FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')
EXAMPLE_DIR = os.path.join(BASE_DIR, 'static', 'example_file', 'block_number_count')
if not os.path.exists(FILE_KEEP_DIR):
    os.makedirs(FILE_KEEP_DIR)

# =========================================================
# 辅助函数
# =========================================================

def index(request):
    """首页导向"""
    return render(request, 'block_number_count.html')

def name_set():
    """生成唯一任务ID文件夹"""
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    folder_path = os.path.join(FILE_KEEP_DIR, folder_name)
    from api.download_access import create_job_directory
    create_job_directory(folder_path)
    return folder_name

def keep_files(files, task_id):
    """保存上传的文件"""
    if not files: return
    target_dir = os.path.join(FILE_KEEP_DIR, task_id)
    for f in files:
        file_path = os.path.join(target_dir, f.name)
        with open(file_path, 'wb+') as destination:
            for chunk in f.chunks():
                destination.write(chunk)

def zip_result(request, task_id, target_filename):
    """
    【方案B核心修改】：压缩并直接返回文件流
    """
    target_dir = os.path.join(FILE_KEEP_DIR, task_id)
    zip_path = os.path.join(target_dir, 'result.zip')
    
    target_file_path = os.path.join(target_dir, target_filename)

    if not os.path.exists(target_file_path):
        return HttpResponse(f"Error: Result file not found.", status=404)

    try:
        # 创建压缩包
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(target_file_path, arcname=target_filename)
            
        # --- 修改开始 ---
        # 不再返回 render 页面，而是直接返回 FileResponse
        # 配合前端 target="hidden_frame"，浏览器会自动下载，主页面不跳转
        if os.path.exists(zip_path):
            response = FileResponse(open(zip_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            # filename 设置为用户下载时看到的文件名
            response['Content-Disposition'] = f'attachment; filename="Block_Stat_Result.zip"'
            return response
        else:
            return HttpResponse("Error: Zip file creation failed.", status=500)
        # --- 修改结束 ---

    except Exception as e:
        return HttpResponse(f"Zip Error: {e}", status=500)

# 注意：虽然方案B不再依赖这个 file_download 函数进行跳转下载，
# 但保留它作为备用下载接口也是可以的，或者你可以选择删除它。
def file_download(request):
    """处理文件下载（方案B中主要逻辑已移至 zip_result，此函数暂时闲置）"""
    file_path_encoded = request.GET.get('file', '')
    if not file_path_encoded:
        return HttpResponse("No file specified", status=400)
    
    file_path = unquote(file_path_encoded)
    
    if 'file_keep' not in os.path.abspath(file_path):
         return HttpResponse("Access Denied", status=403)

    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
    else:
        return HttpResponse("File not found", status=404)

def block_number_count_example_download(request):
    """打包返回 block_number_count 示例文件。"""
    if not os.path.isdir(EXAMPLE_DIR):
        return HttpResponse("Example files not found.", status=404)

    example_files = sorted(
        file_name for file_name in os.listdir(EXAMPLE_DIR)
        if os.path.isfile(os.path.join(EXAMPLE_DIR, file_name))
    )
    if not example_files:
        return HttpResponse("Example files not found.", status=404)

    zip_buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_name in example_files:
                file_path = os.path.join(EXAMPLE_DIR, file_name)
                zip_file.write(file_path, arcname=file_name)
    except Exception as e:
        return HttpResponse(f"Zip Error: {str(e)}", status=500)

    zip_buffer.seek(0)
    response = FileResponse(zip_buffer, as_attachment=True, filename='block_number_count_example.zip')
    response['Content-Type'] = 'application/zip'
    return response

# =========================================================
# 核心业务视图
# =========================================================

def block_number_count(request):
    """渲染功能页面"""
    return render(request, 'block_number_count.html')

def block_number_count_run(request):
    """处理表单提交，运行统计逻辑"""
    try:
        # 1. 获取文件
        files = request.FILES.getlist("file", None)
        if not files:
            return HttpResponse("Please upload files.", status=400)
        
        # 2. 准备环境
        task_id = name_set()
        keep_files(files, task_id)
        
        # 3. 调用 tools.py 中的纯 Python 逻辑
        tools.block_number_count_run_tools(task_id)
        
        # 4. 打包并直接触发下载
        # 结果文件名需对应 tools 生成的文件名
        return zip_result(request, task_id, 'block.all.count.txt')

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Run Error: {str(e)}", status=500)
