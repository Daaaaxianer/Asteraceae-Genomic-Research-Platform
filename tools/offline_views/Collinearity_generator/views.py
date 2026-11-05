import os
import time
import zipfile
import traceback
import uuid
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.urls import reverse

# 尝试导入工具函数
try:
    from .tools import collinearity_generator_run_tools
except ImportError:
    print("❌ Error: Could not import collinearity_generator_run_tools from tools.py")
    traceback.print_exc()

# 基础配置
BASE_DIR = settings.BASE_DIR
FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')
os.makedirs(FILE_KEEP_DIR, exist_ok=True)

# 辅助函数
def create_workspace():
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    folder_path = os.path.join(FILE_KEEP_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_name

def save_uploaded_files(files, workspace_name):
    if not files: return
    target_dir = os.path.join(FILE_KEEP_DIR, workspace_name)
    for f in files:
        file_path = os.path.join(target_dir, f.name)
        with open(file_path, 'wb+') as destination:
            for chunk in f.chunks():
                destination.write(chunk)

# Views
def collinearity_generator(request):
    return render(request, 'collinearity_generator.html')

def collinearity_generator_run(request):
    try:
        if request.method != 'POST':
            return redirect('collinearity_generator_url')

        # 1. 获取参数
        patten = request.POST.get('patten')
        reference_file = request.POST.get('reference_file')
        species_name = request.POST.get('species_name')
        uploaded_files = request.FILES.getlist("file")

        if not uploaded_files:
            return HttpResponse("Error: No files uploaded.", status=400)

        # 2. 创建工作区并保存
        workspace = create_workspace()
        save_uploaded_files(uploaded_files, workspace)

        # 3. 运行算法
        # 注意：这里传递的是 workspace (字符串，文件夹名)
        collinearity_generator_run_tools(
            place=workspace, 
            patten=patten, 
            reference_file=reference_file, 
            species_name=species_name
        )

        # 4. 打包结果
        work_dir = os.path.join(FILE_KEEP_DIR, workspace)
        zip_filename = f'result_{workspace}.zip'
        zip_filepath = os.path.join(work_dir, zip_filename)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            target_file = os.path.join(work_dir, 'output.txt')
            if os.path.exists(target_file):
                zf.write(target_file, arcname='output.txt')
            else:
                # 如果没有output.txt，写入一个错误日志供用户查看
                error_log = os.path.join(work_dir, 'error_log.txt')
                with open(error_log, 'w') as f:
                    f.write("Output file was not generated. Please check your input files format.")
                zf.write(error_log, arcname='error_log.txt')

        # 5. 直接下载
        if os.path.exists(zip_filepath):
            response = FileResponse(open(zip_filepath, 'rb'))
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="Syn_Deco_Result.zip"'
            return response
        else:
            return HttpResponse("Error: Zip file generation failed.", status=500)

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Server Error: {str(e)}", status=500)

# 保留下载接口
def result_download(request, workspace_id):
    pass # 如前
# 保留占位符
def blast(request): return HttpResponse("Module under construction")
def blast_run(request): pass
def blast_match(request): return HttpResponse("Module under construction")
def blast_match_run(request): pass
def f_blast(request): pass
def STK_chart(request): pass
def hierarchical_alignments_eupl(request): pass