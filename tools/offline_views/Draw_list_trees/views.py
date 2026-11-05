# Written by Yu Zijian
# E-main: yuzijian1010@163.com

import os
import sys
import glob
import time
import uuid
import zipfile
import traceback
import shutil
from urllib.parse import quote, unquote

# =========================================================
# 1. 绘图库防崩溃设置
# =========================================================
import matplotlib
# 强制使用非交互式后端，防止在后台运行时崩溃
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings

# 尝试导入同级目录下的 tools.py
try:
    from .tools import draw_list_tree_run_tools
except ImportError:
    print("Warning: tools.py definition not found or circular import.")
    traceback.print_exc()
    # 定义空函数防止启动报错
    def draw_list_tree_run_tools(place, patten): pass


def get_real_base_dir():
    """
    修正后的路径获取逻辑：
    当前文件: .../tools/offline_views/Draw_list_trees/views.py
    目标根目录: .../Asteraceae (即 file_keep 所在目录)
    需要向上回溯 4 层
    """
    current_file_path = os.path.abspath(__file__)
    
    # 1. Draw_list_trees
    dir_1 = os.path.dirname(current_file_path)
    # 2. offline_views
    dir_2 = os.path.dirname(dir_1)
    # 3. tools
    dir_3 = os.path.dirname(dir_2)
    # 4. Asteraceae (Root) - file_keep 在这里
    root_dir = os.path.dirname(dir_3)
    
    return root_dir

# 全局变量：当前工作根目录
path_get = get_real_base_dir()

# 确保必要文件夹存在
required_dirs = ['file_keep', os.path.join('file_keep', 'species_data')]
for d in required_dirs:
    full_path = os.path.join(path_get, d)
    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)

print(f"✅ [View] 当前项目根目录: {path_get}")


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
    with open(file_path, 'wb+') as destination:
        for chunk in na.chunks():
            destination.write(chunk)
    return file_path

def keep_files(na, c):
    """保存多个上传文件"""
    if not na: return
    # 如果传入的是单个文件对象，转为列表
    if not isinstance(na, list):
        na = [na]
    for f in na:
        keep_file(f, c)

def zip_file(request, place, files):
    """
    使用 Python 原生 zipfile 打包结果
    并直接触发浏览器下载 (FileResponse)
    """
    target_dir = os.path.join(path_get, 'file_keep', place)
    zip_filename = 'result.zip'
    zip_filepath = os.path.join(target_dir, zip_filename)

    file_list = []
    
    # 解析文件列表或通配符
    patterns = files.split()
    for pattern in patterns:
        search_path = os.path.join(target_dir, pattern)
        found_files = glob.glob(search_path)
        file_list.extend(found_files)

    # 去重
    file_list = list(set(file_list))

    try:
        if not file_list:
            print(f"Warning: No files found to zip in {target_dir}")
            return HttpResponse("Error: No result files generated.", status=500)
        
        # 创建压缩包
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in file_list:
                # arcname 确保压缩包内不包含服务器绝对路径
                zf.write(file_path, arcname=os.path.basename(file_path))
        
        # =======================================================
        # 修改点：直接返回文件流，而不是跳转页面
        # =======================================================
        if os.path.exists(zip_filepath):
            # 打开文件流 (注意：FileResponse 会自动处理文件关闭，但为了安全通常让它接管句柄)
            response = FileResponse(open(zip_filepath, 'rb'))
            
            # 设置 Content-Type 为 zip
            response['Content-Type'] = 'application/zip'
            
            # 设置 Content-Disposition 为 attachment 触发下载
            # filename 可以自定义，这里暂定为 result.zip
            response['Content-Disposition'] = 'attachment; filename="result.zip"'
            response.set_cookie('draw_list_tree_download', 'done', max_age=60, path='/')
            
            return response
        else:
            return HttpResponse("Error: Zip creation failed.", status=500)
                
    except Exception as e:
        print(f"Zip Error: {e}")
        traceback.print_exc()
        return HttpResponse(f"Server Error during compression: {e}", status=500)
def file_download(request):
    """
    通用下载视图
    """
    try:
        file_path_encoded = request.GET.get('file', '')
        if not file_path_encoded:
            return HttpResponse("No file specified", status=400)
        
        file_path = unquote(file_path_encoded)
        
        # 安全检查：限制只能下载 file_keep 目录下的文件
        abs_file_path = os.path.abspath(file_path)
        if 'file_keep' not in abs_file_path:
             return HttpResponse("Access Denied: File must be in authorized directory.", status=403)
        
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
        else:
            return HttpResponse(f"File not found on server.", status=404)
    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Download Error: {e}", status=500)


# =========================================================
# 视图函数
# =========================================================

def draw_list_tree(request): 
    return render(request, 'draw_list_tree.html')


def draw_list_tree_run(request):
    try:
        if request.method != 'POST':
            return render(request, 'draw_list_tree.html')

        patten = request.POST.get('patten', None)
        file1 = request.FILES.getlist("file1", None)
        file2 = request.FILES.get("file2", None)
        
        if not file1 or not file2:
            return HttpResponse("Error: Please upload all required files.")
            
        c = name_set()
        
        # 强制将 list 文件重命名为 list.txt 以适配 tools.py
        file2.name = "list.txt"
        
        keep_files(na=file1, c=c)
        keep_file(na=file2, c=c)
        
        # 运行核心逻辑
        print(f"Running task in {c}...")
        draw_list_tree_run_tools(place=c, patten=patten)
        
        # 打包结果：打包所有的 png, newick, tree, txt 文件
        # 之前的代码指定了 zip 文件名，但 tools.py 生成的是散文件，所以这里改用通配符
        files_to_zip = '*.png *.newick *.tree *.txt *.pdf' 
        return zip_file(request, c, files_to_zip)
        
    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Error: {e}")
