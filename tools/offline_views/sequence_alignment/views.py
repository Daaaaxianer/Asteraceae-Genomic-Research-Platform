import os
import random
import string
import zipfile
import subprocess
import shutil
from django.shortcuts import render
from django.http import HttpResponse, FileResponse

# ==========================================
# 1. 核心路径配置
# ==========================================

current_file_path = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))))
FILE_KEEP_ROOT = os.path.join(PROJECT_ROOT, 'file_keep')

if not os.path.exists(FILE_KEEP_ROOT):
    try:
        os.makedirs(FILE_KEEP_ROOT)
    except OSError:
        pass

# ==========================================
# 2. 工具函数 (目录与文件管理)
# ==========================================

def name_set():
    """生成随机ID并创建目录"""
    c = ''.join(random.sample(string.digits, 9))
    target_dir = os.path.join(FILE_KEEP_ROOT, c)
    from api.download_access import create_job_directory
    create_job_directory(target_dir)
    return c

def keep_file(file_obj, folder_id, rename_to=None):
    """保存上传文件"""
    if rename_to:
        file_name = rename_to
    else:
        file_name = file_obj.name

    destination_path = os.path.join(FILE_KEEP_ROOT, folder_id, file_name)

    with open(destination_path, 'wb+') as f:
        for chunk in file_obj.chunks():
            f.write(chunk)
            
    return destination_path

def run_command(cmd, work_dir):
    """
    执行 Shell 命令的辅助函数
    【关键修复】：注入完整的 PATH 环境变量，解决 mafft 内部报错问题
    """
    # 1. 复制当前环境
    env = os.environ.copy()
    
    # 2. 强制补充 Linux 标准命令路径
    # 解决 "dirname: command not found", "grep: command not found" 等错误
    base_path = "/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin"
    current_path = env.get('PATH', '')
    env['PATH'] = f"{base_path}:{current_path}"
    
    # 3. 根据 MAFFT 报错要求，清理冲突变量
    # "This variable must be *unset*"
    if 'MAFFT_BINARIES' in env:
        del env['MAFFT_BINARIES']

    try:
        # 注意：这里传入了 env 参数
        subprocess.run(cmd, shell=True, check=True, cwd=work_dir, stderr=subprocess.PIPE, env=env)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode(errors='ignore') if e.stderr else str(e)
        # 打印错误到后台日志
        print(f"Command Error: {error_msg}")
        raise RuntimeError(f"Alignment tool failed. Error: {error_msg}")

def sequence_aligment_run_tools(place, patten):
    """
    执行比对工具逻辑
    """
    work_dir = os.path.join(FILE_KEEP_ROOT, place)
    input_file = "1.fasta"
    
    input_path = os.path.join(work_dir, input_file)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file missing at: {input_path}")

    # =======================================================
    # 配置服务器上的工具绝对路径
    # =======================================================
    MAFFT_BIN = "/usr/local/bin/mafft"
    MUSCLE_BIN = "/usr/bin/muscle"
    CLUSTALW_BIN = "/usr/local/bin/clustalw2"
    # =======================================================

    if patten == "mafft":
        output_file = "mafft.fasta"
        cmd = f"{MAFFT_BIN} --auto {input_file} > {output_file}"
        run_command(cmd, work_dir)

    elif patten == "muscle":
        output_file = "1.aln"
        cmd = f"{MUSCLE_BIN} -in {input_file} -out {output_file}"
        run_command(cmd, work_dir)

    elif patten == "clustalw2":
        output_file = "1.aln"
        cmd = f"{CLUSTALW_BIN} -infile={input_file} -outfile={output_file}"
        run_command(cmd, work_dir)
    
    else:
        raise ValueError(f"Unknown tool: {patten}")

# ==========================================
# 3. 压缩与下载逻辑
# ==========================================

def create_zip_response(folder_id, target_filename):
    folder_path = os.path.join(FILE_KEEP_ROOT, folder_id)
    source_file_path = os.path.join(folder_path, target_filename)
    zip_file_path = os.path.join(folder_path, 'result.zip')

    if not os.path.exists(source_file_path):
        return HttpResponse(f"Error: Result file '{target_filename}' was not generated. Please check logs.", status=404)

    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(source_file_path, arcname=target_filename)
        
        response = FileResponse(open(zip_file_path, 'rb'))
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename="result.zip"'
        response.set_cookie('sequence_alignment_download', 'done', max_age=60, path='/')
        return response

    except Exception as e:
        return HttpResponse(f"Error creating zip: {str(e)}", status=500)

# ==========================================
# 4. Django Views 视图函数
# ==========================================

def sequence_alignment(request):
    return render(request, 'sequence_alignment.html')

def sequence_alignment_run(request):
    if request.method != 'POST':
        return render(request, 'sequence_alignment.html')

    myFile1 = request.FILES.get("file1", None)
    patten = request.POST.get('patten', None)

    if myFile1 is None:
        return HttpResponse("No file uploaded", status=400)

    try:
        c = name_set()
        keep_file(myFile1, c, rename_to="1.fasta")
        sequence_aligment_run_tools(place=c, patten=patten)

        if patten == "mafft":
            result_file = "mafft.fasta"
        else:
            result_file = "1.aln"

        return create_zip_response(c, result_file)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f"An error occurred during processing: <br><pre>{str(e)}</pre>", status=500)
