# Written by Yu Zijian
# Refactored for Web Integration (Block Dotplot)

import os
import sys
import glob
import time
import zipfile
import traceback
from urllib.parse import unquote

from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# 导入 tools 函数
try:
    from .tools import zu_block_dotplot_run_tools
except ImportError:
    print("❌ Error: Could not import tools. Check if tools/tools.py exists.")
    traceback.print_exc()

# =========================================================
# 1. 基础环境配置
# =========================================================

# 确保文件存储在项目根目录下的 file_keep 文件夹中
path_get = settings.BASE_DIR
file_keep_dir = os.path.join(path_get, 'file_keep')

if not os.path.exists(file_keep_dir):
    os.makedirs(file_keep_dir)

print(f"✅ [View] Storage: {file_keep_dir}")

# =========================================================
# 2. 辅助工具函数
# =========================================================

def name_set():
    """生成唯一的工作目录名"""
    import uuid
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:8]}"
    folder_path = os.path.join(file_keep_dir, folder_name)
    from api.download_access import create_job_directory
    create_job_directory(folder_path)
    return folder_name

def save_as_standardized(file_obj, folder_name, target_filename):
    """保存并重命名文件"""
    if not file_obj: 
        return None
    
    target_dir = os.path.join(file_keep_dir, folder_name)
    target_path = os.path.join(target_dir, target_filename)
    
    with open(target_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
            
    return target_path

def zip_and_respond(request, folder_name, file_pattern="*.png"):
    """打包结果并返回"""
    target_dir = os.path.join(file_keep_dir, folder_name)
    zip_filename = f'result_{folder_name}.zip'
    zip_filepath = os.path.join(target_dir, zip_filename)

    # 查找 png 和 pdf
    files_to_zip = glob.glob(os.path.join(target_dir, file_pattern))
    files_to_zip.extend(glob.glob(os.path.join(target_dir, "*.pdf")))

    if not files_to_zip:
        return HttpResponse(f"Analysis finished, but no output images found in {target_dir}.<br>Please check your input data (headers, IDs, etc).", status=200)

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in files_to_zip:
                zf.write(file_path, arcname=os.path.basename(file_path))
    except Exception as e:
        return HttpResponse(f"Error creating zip file: {e}")

    response = FileResponse(open(zip_filepath, 'rb'), as_attachment=True, filename="Result_Dotplot.zip")
    response.set_cookie('zu_block_dotplot_download', 'done', max_age=60, path='/')
    return response

# =========================================================
# 3. 核心业务视图
# =========================================================

def index(request):
    """首页渲染"""
    return render(request, 'zu_block_dotplot.html')

def zu_block_dotplot_run(request):
    """点击 'Run' 后的处理逻辑"""
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    try:
        # 1. 接收文件
        f_shu_len = request.FILES.get('shu_len')
        f_shu_gff = request.FILES.get('shu_gff')
        f_heng_len = request.FILES.get('heng_len')
        f_heng_gff = request.FILES.get('heng_gff')
        f_blast = request.FILES.get('blast')
        f_block = request.FILES.get('block')
        
        # 接收参数
        block_num = request.POST.get('block_num', '10')

        # 2. 校验文件
        if not all([f_shu_len, f_shu_gff, f_heng_len, f_heng_gff, f_blast, f_block]):
            return HttpResponse("<h3>Error: Missing files.</h3><p>Please check your upload.</p>")

        # 3. 创建工作目录
        c = name_set() 
        
        # 4. 保存文件 (标准化命名，配合 tools.py 的逻辑)
        name1 = "Species1"
        name2 = "Species2"

        save_as_standardized(f_shu_len, c, f"{name1}.lens")
        save_as_standardized(f_shu_gff, c, f"{name1}.new.gff")
        
        save_as_standardized(f_heng_len, c, f"{name2}.lens")
        save_as_standardized(f_heng_gff, c, f"{name2}.new.gff")

        save_as_standardized(f_blast, c, f"{name1}_{name2}.blast")
        save_as_standardized(f_block, c, f"{name1}_{name2}.block.rr.txt")

        print(f"✅ Analysis Started in: {c}")

        # 5. 调用 Tools
        zu_block_dotplot_run_tools(
            place=c, 
            name1=name1,
            name2=name2,
            block_num=block_num
        )

        # 6. 打包并返回
        return zip_and_respond(request, c, "*.png")

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"<h2>Analysis Error</h2><pre>{str(e)}</pre>")

def file_download(request):
    """文件下载接口"""
    file_path = unquote(request.GET.get('file', ''))
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True)
    return HttpResponse("File not found")
