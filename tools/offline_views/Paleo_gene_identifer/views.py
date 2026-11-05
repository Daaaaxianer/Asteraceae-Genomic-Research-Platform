# Written by Yu Zijian
# E-main: yuzijian1010@163.com

import os
import sys
import glob
import time
import zipfile
import traceback
import uuid
from urllib.parse import quote, unquote

# =========================================================
# 1. 绘图库防崩溃设置
# =========================================================
import matplotlib
# 强制使用非交互式后端，防止在后台运行时因为试图弹出窗口而崩溃
matplotlib.use('Agg') 
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.conf import settings

# 尝试导入同目录下的 tools.py
try:
    from .tools import zu_correspondence_mc_run_tools
except ImportError:
    print("Error: tools.py module not found.")
    traceback.print_exc()
    def zu_correspondence_mc_run_tools(*args, **kwargs):
        raise ImportError("The tools.py module is missing; the analysis cannot run.")

# =========================================================
# 2. 核心路径逻辑
# =========================================================
def get_real_base_dir():
    """定位项目根目录"""
    if hasattr(settings, 'BASE_DIR'):
        return str(settings.BASE_DIR)
    current_file_dir = os.path.dirname(os.path.abspath(__file__)) 
    project_root = os.path.dirname(current_file_dir)
    return project_root

path_get = get_real_base_dir()

# 确保基础文件夹存在
required_dirs = ['file_keep']
for d in required_dirs:
    full_path = os.path.join(path_get, d)
    if not os.path.exists(full_path):
        os.makedirs(full_path)

# =========================================================
# 3. 文件操作辅助函数
# =========================================================
def name_set():
    """生成唯一的工作目录名"""
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    from api.download_access import create_job_directory
    create_job_directory(os.path.join(str(settings.BASE_DIR), 'file_keep', folder_name))
    return folder_name

def keep_file(na, c, rename_to=None):
    """保存单个上传文件，确保目录存在"""
    if not na: return None
    
    # 构建绝对路径
    target_dir = os.path.join(path_get, 'file_keep', c)
    
    # 确保目录存在
    if not os.path.exists(target_dir):
        from api.download_access import create_job_directory
        create_job_directory(target_dir)
    
    final_name = rename_to if rename_to else na.name
    file_path = os.path.join(target_dir, final_name)
    
    try:
        with open(file_path, 'wb+') as destination:
            for chunk in na.chunks():
                destination.write(chunk)
        return file_path
    except Exception as e:
        print(f"File Save Error: {e}")
        return None

def zip_file(request, place, files_pattern):
    """
    【修改版】打包文件并直接触发浏览器下载，不跳转页面
    """
    target_dir = os.path.join(path_get, 'file_keep', place)
    zip_filename = f'Result_{place}.zip' # 设置下载文件名
    zip_filepath = os.path.join(target_dir, zip_filename)

    file_list = []
    patterns = files_pattern.split()
    for pat in patterns:
        search_path = os.path.join(target_dir, pat)
        found_files = glob.glob(search_path)
        file_list.extend(found_files)
    
    file_list = list(set(file_list))

    try:
        # 创建 ZIP 包
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in file_list:
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=os.path.basename(file_path))
        
        # 直接返回文件流，浏览器会自动下载
        if os.path.exists(zip_filepath):
            response = FileResponse(open(zip_filepath, 'rb'))
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            return response
        else:
            return HttpResponse("Error: Zip file creation failed.", status=500)

    except Exception as e:
        print(f"Zip Error: {e}")
        return HttpResponse(f"Server Error during zipping: {e}", status=500)

# =========================================================
# 4. 视图函数
# =========================================================

def file_download(request):
    """独立的下载接口（保留以备不时之需）"""
    try:
        file_path_encoded = request.GET.get('file', '')
        if not file_path_encoded:
            return HttpResponse("No file specified", status=400)
        
        file_path = unquote(file_path_encoded)
        abs_file_path = os.path.abspath(file_path)
        abs_keep_dir = os.path.abspath(os.path.join(path_get, 'file_keep'))
        
        if not abs_file_path.startswith(abs_keep_dir):
             return HttpResponse("Access Denied.", status=403)
        
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
        else:
            return HttpResponse(f"File not found.", status=404)
    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Download Error: {e}", status=500)

def zu_correspondence_mc_html(request):
    return render(request, 'zu_correspondence_mc.html')

def zu_correspondence_mc_run(request):
    if request.method != 'POST':
        return HttpResponseRedirect('/')

    try:
        # 1. 获取 Species Name
        shu_name = request.POST.get('shu_species', '').strip()
        heng_name = request.POST.get('heng_species', '').strip()
        
        # 兜底：从文件名推断
        if not shu_name and request.FILES.get('shu_len'):
            shu_name = os.path.splitext(request.FILES.get('shu_len').name)[0]
        if not heng_name and request.FILES.get('heng_len'):
            heng_name = os.path.splitext(request.FILES.get('heng_len').name)[0]

        if not shu_name or not heng_name:
             return HttpResponse("Error: Species names are required.", status=400)

        # 2. 获取文件
        files_map = {
            'blast': request.FILES.get('blast'),
            'block': request.FILES.get('block_file'),
            'corr': request.FILES.get('correspondence_file'),
            'shu_len': request.FILES.get('shu_len'),
            'shu_gff': request.FILES.get('shu_gff'),
            'heng_len': request.FILES.get('heng_len'),
            'heng_gff': request.FILES.get('heng_gff'),
        }

        if not all(files_map.values()):
            return HttpResponse("Missing required files.", status=400)

        # 3. 创建路径 ID
        c = name_set()
        
        # 计算绝对路径
        target_dir = os.path.join(path_get, 'file_keep', c)
        if not os.path.exists(target_dir):
            from api.download_access import create_job_directory
            create_job_directory(target_dir)

        # 4. 保存并重命名
        keep_file(files_map['blast'], c, rename_to=f"{shu_name}_{heng_name}.blast")
        keep_file(files_map['block'], c, rename_to=f"{shu_name}_{heng_name}.block.rr.txt")
        keep_file(files_map['corr'], c, rename_to=f"{shu_name}_{heng_name}.txt")
        
        keep_file(files_map['shu_len'], c, rename_to=f"{shu_name}.lens")
        keep_file(files_map['shu_gff'], c, rename_to=f"{shu_name}.new.gff")
        
        keep_file(files_map['heng_len'], c, rename_to=f"{heng_name}.lens")
        keep_file(files_map['heng_gff'], c, rename_to=f"{heng_name}.new.gff")

        # 5. 调用工具 (传递绝对路径)
        zu_correspondence_mc_run_tools(full_work_dir=target_dir, shu_name=shu_name, heng_name=heng_name)

        # 6. 打包并直接返回文件流 (直接下载)
        files_pattern = f"*new.blast *.mc.*.txt *_corr.png *.corr.txt"
        return zip_file(request, c, files_pattern)

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Run Error: {str(e)}", status=500)
