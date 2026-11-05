import os
import shutil
import subprocess
import random
import string
import zipfile
import logging
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings

# 设置日志
logger = logging.getLogger(__name__)

# ==========================================
# 1. 路径与配置
# ==========================================

# 确保 file_keep 目录存在
FILE_KEEP_DIR = os.path.join(settings.BASE_DIR, 'file_keep')
if not os.path.exists(FILE_KEEP_DIR):
    os.makedirs(FILE_KEEP_DIR, exist_ok=True)

# 工具绝对路径 (根据你提供的路径)
PATH_HMMBUILD = "/www/tools/hmmer-3.3.1/src/hmmbuild"
PATH_HMMSEARCH = "/usr/local/bin/hmmsearch"


# ==========================================
# 2. 辅助工具函数
# ==========================================

def create_job_dir():
    """在 file_keep 中创建一个随机命名的工作目录"""
    job_id = ''.join(random.sample(string.digits, 9))
    job_path = os.path.join(FILE_KEEP_DIR, job_id)
    
    while os.path.exists(job_path):
        job_id = ''.join(random.sample(string.digits, 9))
        job_path = os.path.join(FILE_KEEP_DIR, job_id)
        
    os.makedirs(job_path, exist_ok=True)
    return job_id, job_path

def save_uploaded_file(file_obj, destination_dir):
    """保存上传的文件，保留原始文件名"""
    file_path = os.path.join(destination_dir, file_obj.name)
    with open(file_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    return file_path

def create_zip_archive(source_dir, output_filename, files_to_include):
    """压缩文件"""
    zip_path = os.path.join(source_dir, output_filename)
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files_to_include:
                file_abs_path = os.path.join(source_dir, file)
                if os.path.exists(file_abs_path):
                    zipf.write(file_abs_path, arcname=file)
        return zip_path
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        return None

def is_hmm_file(file_path):
    """
    检查文件是否已经是 HMMER3 格式的模型文件
    读取文件前几行看是否有 'HMMER3' 标志
    """
    try:
        with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
            # 读取前 100 个字符通常就够了
            head = f.read(100)
            return 'HMMER3' in head
    except Exception:
        return False

def run_hmmer_process(work_dir, model_file_path, target_seq_path, e_value):
    """
    执行 Hmmer 流程 (智能判断模式)
    
    参数:
      work_dir: 工作目录
      model_file_path: 用户上传的模型文件路径 (可能是 .hmm 也可能是 .fasta)
      target_seq_path: 用户上传的序列数据库路径 (如 .pep)
      e_value: 阈值
    """
    
    hmm_ready_path = "" # 最终用于搜索的 .hmm 文件路径
    result_file = "result.out"
    
    # ==========================================
    # 步骤 1: 准备 HMM 模型
    # ==========================================
    
    # A. 如果上传的已经是 HMM 文件 (如 SRF-TF.hmm)
    if is_hmm_file(model_file_path):
        hmm_ready_path = model_file_path
        
    # B. 如果上传的是序列文件，需要先 hmmbuild
    else:
        output_hmm = os.path.join(work_dir, "built_model.hmm")
        
        # B-1. 清洗格式 (防止 Windows 换行符报错)
        try:
            with open(model_file_path, 'rb') as f:
                content = f.read().replace(b'\r\n', b'\n')
            with open(model_file_path, 'wb') as f:
                f.write(content)
        except Exception as e:
            return False, f"File preprocessing failed: {str(e)}"

        # B-2. 执行 hmmbuild
        # 命令格式: hmmbuild <输出.hmm> <输入.fasta>
        cmd_build = [PATH_HMMBUILD, output_hmm, model_file_path]
        
        try:
            subprocess.run(cmd_build, cwd=work_dir, check=True, capture_output=True, text=True)
            hmm_ready_path = output_hmm # 标记构建好的文件为下一步的输入
        except subprocess.CalledProcessError as e:
            error_msg = f"HMM Build Failed.\nCommand: {e.cmd[0]}\nError: {e.stderr}\n\nHint: Make sure your input file is either a valid .hmm file or an ALIGNED fasta file."
            logger.error(error_msg)
            return False, error_msg

    # ==========================================
    # 步骤 2: 执行 HMM 搜索 (hmmsearch)
    # ==========================================
    
    # 命令格式: hmmsearch -o <输出> --noali -E <阈值> <模型.hmm> <目标序列>
    cmd_search = [PATH_HMMSEARCH, "-o", result_file, "--noali", "-E", str(e_value), hmm_ready_path, target_seq_path]

    try:
        subprocess.run(cmd_search, cwd=work_dir, check=True, capture_output=True, text=True)
        return True, "Success"
        
    except subprocess.CalledProcessError as e:
        error_msg = f"HMM Search Failed.\nCommand: {e.cmd[0]}\nError: {e.stderr}"
        logger.error(error_msg)
        return False, error_msg
        
    except FileNotFoundError:
        return False, "HMMER executable not found. Please check PATH configurations."


# ==========================================
# 3. 视图函数 (Views)
# ==========================================

def tools(request):
    return render(request, 'tools.html')

def hmmer(request):
    return render(request, 'hmmer.html')

def hmmer_run(request):
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    # 1. 获取上传的文件和参数
    # model_file 对应你的 SRF-TF.hmm
    model_file = request.FILES.get("hmm_model")
    # target_file 对应你的 Aann.pep
    target_file = request.FILES.get('hmm_fa')
    
    e_value = request.POST.get('e_value', '1e-5')

    if not model_file or not target_file:
        return render(request, 'hmmer.html', {"error": "Missing files"})

    # 2. 创建工作空间
    job_id, job_path = create_job_dir()

    try:
        # 3. 保存文件 (保留原名，不再强制改名，以便调试和识别)
        path_model = save_uploaded_file(model_file, job_path)
        path_target = save_uploaded_file(target_file, job_path)

        # 4. 运行智能流程
        success, msg = run_hmmer_process(job_path, path_model, path_target, e_value)
        
        if not success:
            # 失败反馈
            return HttpResponse(f"""
                <h3 style="color:red">Analysis Failed</h3>
                <p><strong>Job ID:</strong> {job_id}</p>
                <p><strong>Reason:</strong></p>
                <pre>{msg}</pre>
            """, status=500)

        # 5. 压缩结果
        # 只要 result.out
        target_files = ['result.out']
        zip_file_path = create_zip_archive(job_path, 'result.zip', target_files)

        if zip_file_path and os.path.exists(zip_file_path):
            response = FileResponse(open(zip_file_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="hmmer_result_{job_id}.zip"'
            response.set_cookie('hmmer_download', 'done', max_age=60, path='/')
            return response
        else:
            return HttpResponse("Analysis finished but result file generation failed.", status=500)

    except Exception as e:
        logger.error(f"Unexpected error in hmmer_run: {e}")
        return HttpResponse(f"Server Error: {str(e)}", status=500)
