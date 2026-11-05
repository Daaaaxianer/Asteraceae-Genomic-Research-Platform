import os
import time
import zipfile
import traceback
import uuid
import sys
from urllib.parse import quote, unquote
from django.shortcuts import render
from django.http import HttpResponse, FileResponse, Http404

# 导入同级目录下的 tools.py
try:
    from .tools import zu_pindex_run_tools
except ImportError:
    pass

# =========================================================
# 1. 路径与环境配置
# =========================================================

def get_real_base_dir():
    """
    获取项目根目录，适配深层嵌套结构
    目标：从 tools/offline_views/Paleo_gene_RII/views.py 回退到 Asteraceae/
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    
    current_file = os.path.abspath(__file__)
    
    # 逐级向上回退 4 层以找到 file_keep 所在的根目录
    # 1. .../Paleo_gene_RII (当前文件所在目录)
    # 2. .../offline_views
    # 3. .../tools
    # 4. .../Asteraceae (目标根目录)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))

PATH_GET = get_real_base_dir()
KEEP_DIR = os.path.join(PATH_GET, 'file_keep')

# 自动创建必要目录
os.makedirs(os.path.join(KEEP_DIR, 'species_data'), exist_ok=True)

# =========================================================
# 2. 核心视图函数
# =========================================================

def zu_pindex_run(request):
    """主计算视图"""
    if request.method != 'POST':
        return render(request, 'zu_pindex.html')

    try:
        # 1. 获取文件
        mc_file = request.FILES.get("mc_file")
        if not mc_file:
            return HttpResponse("Error: No file uploaded.", status=400)

        # 2. 获取参数
        try:
            sliding_window = int(request.POST.get('sliding_window', '100'))
            buchang = int(request.POST.get('buchang', '2'))
            sigema_start = float(request.POST.get('sigema_start', '0.05'))
            sigema_end = float(request.POST.get('sigema_end', '1.8'))
            
            params = {
                'sliding_window': sliding_window,
                'buchang': buchang,
                'sigema_start': sigema_start,
                'sigema_end': sigema_end
            }
        except ValueError:
             return HttpResponse("Error: Parameters must be valid numbers.", status=400)

        # 3. 创建目录
        task_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
        task_path = os.path.join(KEEP_DIR, task_id)
        os.makedirs(task_path, exist_ok=True)

        # 4. 保存文件 (input_data.txt)
        file_path = os.path.join(task_path, 'input_data.txt')
        with open(file_path, 'wb+') as destination:
            for chunk in mc_file.chunks():
                destination.write(chunk)

        # 5. 运行计算
        # 注意：请确保 tools.py 中的路径逻辑也已经同步修改，否则它可能找不到 p_index.py
        zu_pindex_run_tools(place=task_id, **params)

        # 6. 打包 Zip
        zip_filename = 'result.zip'
        zip_filepath = os.path.join(task_path, zip_filename)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            out_dir = os.path.join(task_path, 'output')
            if os.path.exists(out_dir):
                for root, _, files in os.walk(out_dir):
                    for f in files:
                        abs_p = os.path.join(root, f)
                        zf.write(abs_p, arcname=os.path.join('output', f))
            
            log_p = os.path.join(task_path, 'pindex_result.txt')
            if os.path.exists(log_p):
                zf.write(log_p, arcname='pindex_result.txt')

        # 7. 直接触发下载，不再跳转 HTML 页面
        if os.path.exists(zip_filepath):
            response = FileResponse(open(zip_filepath, 'rb'), as_attachment=True)
            response.set_cookie('zu_pindex_download', 'done', max_age=60, path='/')
            # 设置下载时的文件名
            response['Content-Disposition'] = f'attachment; filename="P_Index_Result_{task_id}.zip"'
            return response
        else:
            return HttpResponse("Error: Output file generation failed.", status=500)

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Server Internal Error: {str(e)}", status=500)

# (可选) 单独的下载接口保留，以防万一需要通过链接下载
def file_download(request):
    task_id = request.GET.get('task_id', '')
    if not task_id: return HttpResponse("Invalid request.", status=400)
    
    target_zip = os.path.abspath(os.path.join(KEEP_DIR, task_id, 'result.zip'))
    
    if not target_zip.startswith(os.path.abspath(KEEP_DIR)): 
        return HttpResponse("Access Denied.", status=403)
        
    if os.path.exists(target_zip):
        response = FileResponse(open(target_zip, 'rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="P_Index_Result_{task_id}.zip"'
        return response
    return HttpResponse("File not found.", status=404)
