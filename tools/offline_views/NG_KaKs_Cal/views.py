#views.py
import os
import time
import zipfile
import traceback
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings
from . import tools

# ================= 通用工具 =================


def save_file(file_obj, folder, save_as_name):
    if not file_obj: return
    path = os.path.join(settings.BASE_DIR, 'file_keep', folder)
    if not os.path.exists(path): os.makedirs(path)
    with open(os.path.join(path, save_as_name), 'wb+') as destination:
        for chunk in file_obj.chunks(): destination.write(chunk)

def zip_and_download(request, place):
    """
    修改后：计算完成后直接触发浏览器下载 ZIP 包
    """
    work_dir = os.path.join(str(settings.BASE_DIR), 'file_keep', place)
    ks_dir = os.path.join(work_dir, 'ks') 
    
    zip_filename = f"KaKs_Result_{place}.zip"
    zip_file_path = os.path.join(work_dir, zip_filename)

    # 逻辑判断：如果 ks 文件夹存在且有内容，只打包 ks；否则打包整个目录
    target_dir_to_zip = work_dir 
    if os.path.exists(ks_dir) and os.listdir(ks_dir):
        target_dir_to_zip = ks_dir

    # 执行打包
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(target_dir_to_zip):
            for file in files:
                if file == zip_filename: continue 
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, target_dir_to_zip)
                zipf.write(file_path, arcname)

    # --- 关键修改开始 ---
    # 不再渲染 HTML，而是直接打开文件并返回流
    if os.path.exists(zip_file_path):
        response = FileResponse(open(zip_file_path, 'rb'))
        response['Content-Type'] = 'application/octet-stream'
        # 设置 attachment 使得浏览器强制下载而不是尝试预览
        response['Content-Disposition'] = f'attachment;filename="{zip_filename}"'
        return response
    else:
        return HttpResponse("Error: Zip file generation failed.", status=500)

def download_file(request):
    """
    文件下载响应函数
    """
    place = request.GET.get('place')
    filename = request.GET.get('filename')
    
    if not place or not filename:
        return HttpResponse("Invalid parameters.", status=400)

    # 安全构建路径
    file_path = os.path.join(str(settings.BASE_DIR), 'file_keep', place, filename)
    
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment;filename="{filename}"'
        return response
    else:
        return HttpResponse("File not found", status=404)

# ================= KaKs 核心逻辑 =================

def zu_ks_calculate(request):
    return render(request, 'zu_ks_calculate.html')

def zu_ks_calculate_run(request):
    if request.method != 'POST': return HttpResponse("Please use POST.")
    try:
        c = str(int(time.time()))
        
        # 1. 接收文件
        f1 = request.FILES.get('cds1') 
        f2 = request.FILES.get('cds2') 
        fb = request.FILES.get('block')

        if not f1 or not f2 or not fb:
            return HttpResponse("Error: Please upload all 3 files (Spec1, Spec2, Block).", status=400)

        # 2. 保存文件
        save_file(f1, c, '1.cds')
        save_file(f2, c, '2.cds')
        save_file(fb, c, 'block.txt')

        # 3. 调用 tools (执行计算)
        # 这里的 tools.py 必须是我刚刚发给你的版本(带有 validate_ids 和 merge 逻辑)
        tools.zu_ks_calculate_run_tools(c)
        
        # 4. 打包并跳转
        return zip_and_download(request, c)

    except Exception as e:
        traceback.print_exc()
        # 美化报错页面
        return HttpResponse(f"""
            <div style="padding: 20px; font-family: sans-serif; color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; margin: 20px;">
                <h3>Calculation Failed</h3>
                <p><strong>Error Details:</strong></p>
                <pre>{str(e)}</pre>
                <br>
                <a href="/">Go Back</a>
            </div>
        """, status=500)