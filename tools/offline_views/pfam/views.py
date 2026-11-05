import os
import random
import string
import shutil
import subprocess
import zipfile
import sys
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse

# ================= 1. 自动配置区域 (Auto Discovery) =================

# 定义搜索的根目录列表
SEARCH_ROOTS = [
    '/wangjp', 
    '/home',
    '/usr/local/bin',
    '/opt',
    os.getcwd()
]

# --- Perl 解释器路径 ---
PERL_EXE = '/usr/bin/perl'

# --- 关键修改：HMMER 工具包路径 ---
# 根据之前的 'which hmmscan' 结果 (/usr/local/bin/hmmscan)
# 我们需要把这个目录加到环境变量中，否则 pfam_scan.pl 会报错
HMMER_BIN_DIR = '/usr/local/bin'

# 默认工具路径
DEFAULT_EXE_PATH = '/wangjp/yuzijian/tools/PfamScan/pfam_scan.pl'
DEFAULT_DB_PATH = '/wangjp/yuzijian/tools/PfamScan/pfamdata/'

def find_path(filename, search_roots, is_dir=False, max_depth=5):
    """
    在指定目录中搜索文件或文件夹
    """
    print(f"[Auto-Config] Searching for '{filename}' in {search_roots}...")
    
    for root_path in search_roots:
        if not os.path.exists(root_path):
            continue
            
        for root, dirs, files in os.walk(root_path):
            depth = root[len(root_path):].count(os.sep)
            if depth > max_depth:
                del dirs[:]
                continue
                
            if is_dir:
                if filename in files: 
                    return root + os.sep
            else:
                if filename in files:
                    return os.path.join(root, filename)
    return None

# --- 1.1 自动查找 Pfam 数据库目录 ---
found_db = find_path("Pfam-A.hmm", SEARCH_ROOTS, is_dir=True)
if found_db:
    PFAM_DB_DIR = found_db
    print(f"✅ [Success] Pfam Database found at: {PFAM_DB_DIR}")
else:
    PFAM_DB_DIR = DEFAULT_DB_PATH
    print(f"⚠️ [Warning] Pfam Database not found automatically. Using default: {PFAM_DB_DIR}")

# --- 1.2 自动查找 pfam_scan.pl ---
sys_exe = shutil.which("pfam_scan.pl")
if sys_exe:
    PFAM_SCAN_EXE = sys_exe
    print(f"✅ [Success] pfam_scan.pl found in System PATH: {PFAM_SCAN_EXE}")
else:
    found_exe = find_path("pfam_scan.pl", SEARCH_ROOTS, is_dir=False)
    if found_exe:
        PFAM_SCAN_EXE = found_exe
        print(f"✅ [Success] pfam_scan.pl found at: {PFAM_SCAN_EXE}")
    else:
        PFAM_SCAN_EXE = DEFAULT_EXE_PATH
        print(f"⚠️ [Warning] pfam_scan.pl not found automatically. Using default: {PFAM_SCAN_EXE}")


# ================= 2. 核心配置区域 =================

FILE_KEEP_ROOT = '/wangjp/Asteraceae/Asteraceae/file_keep'

if not os.path.exists(FILE_KEEP_ROOT):
    try:
        os.makedirs(FILE_KEEP_ROOT, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory {FILE_KEEP_ROOT}: {e}")

# ================= 3. 工具函数 =================

def get_random_dir_name():
    return ''.join(random.sample(string.digits, 9))

def save_uploaded_file(file_obj, dir_code):
    target_dir = os.path.join(FILE_KEEP_ROOT, dir_code)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    file_path = os.path.join(target_dir, "1.fasta")
    with open(file_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    return file_path

def run_pfam_scan_logic(dir_code, structure_keywords):
    """
    运行 PfamScan 并根据关键词过滤结果
    """
    work_dir = os.path.join(FILE_KEEP_ROOT, dir_code)
    input_fasta = os.path.join(work_dir, "1.fasta")
    output_raw = os.path.join(work_dir, "pfam.txt")
    output_filtered = os.path.join(work_dir, "pfam_new.txt")

    # 1. 构造命令
    cmd = [
        PERL_EXE,       # /usr/bin/perl
        PFAM_SCAN_EXE,  # 脚本路径
        "-fasta", input_fasta,
        "-dir", PFAM_DB_DIR, 
        "-outfile", output_raw,
        "-cpu", "4"
    ]
    
    # --- 关键修复开始：设置环境变量 ---
    # 复制当前系统的环境变量
    my_env = os.environ.copy()
    # 强制将 HMMER 路径加到 PATH 的最前面，确保脚本能找到 hmmscan
    if HMMER_BIN_DIR:
        my_env["PATH"] = HMMER_BIN_DIR + os.pathsep + my_env.get("PATH", "")
    # --- 关键修复结束 ---

    # 2. 执行命令
    try:
        # 调试信息
        print(f"running cmd: {' '.join(cmd)}")
        print(f"using PATH: {my_env.get('PATH')}")
        
        if not os.path.exists(PFAM_SCAN_EXE):
             raise FileNotFoundError(f"Script not found at {PFAM_SCAN_EXE}")

        subprocess.run(
            cmd, 
            cwd=work_dir, 
            check=True, 
            capture_output=True, 
            text=True,
            env=my_env  # <--- 必须传入修改后的环境变量
        )
        
    except subprocess.CalledProcessError as e:
        with open(output_raw, 'w') as f:
            f.write(f"Error running pfam_scan:\n")
            f.write(f"CMD: {' '.join(cmd)}\n")
            f.write(f"STDERR: {e.stderr}\n")
            f.write(f"STDOUT: {e.stdout}\n")
        # 生成空文件避免报错
        if not os.path.exists(output_filtered):
            open(output_filtered, 'w').close()
        return

    except Exception as e:
        with open(output_raw, 'w') as f:
            f.write(f"System Error: {str(e)}\n")
            f.write(f"Check PERL_EXE: {PERL_EXE}")
        if not os.path.exists(output_filtered):
            open(output_filtered, 'w').close()
        return

    # 3. 结果过滤
    if not structure_keywords or not structure_keywords.strip():
        if os.path.exists(output_raw):
            shutil.copy(output_raw, output_filtered)
        return

    keywords = [k.strip() for k in structure_keywords.replace(';', ',').split(',') if k.strip()]
    
    if os.path.exists(output_raw):
        with open(output_raw, 'r') as fr, open(output_filtered, 'w') as fw:
            for line in fr:
                if line.startswith("#") or line.startswith("<") or not line.strip():
                    fw.write(line)
                    continue
                
                if any(k in line for k in keywords):
                    fw.write(line)

def create_zip_response(dir_code, file_names_str):
    work_dir = os.path.join(FILE_KEEP_ROOT, dir_code)
    zip_filename = "result.zip"
    zip_file_path = os.path.join(work_dir, zip_filename)
    
    file_list = file_names_str.split()
    
    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_name in file_list:
                file_abs_path = os.path.join(work_dir, file_name)
                if os.path.exists(file_abs_path):
                    zipf.write(file_abs_path, arcname=file_name)
    except Exception as e:
        return HttpResponse(f"Error creating zip: {str(e)}", status=500)

    if os.path.exists(zip_file_path):
        response = FileResponse(open(zip_file_path, 'rb'))
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = f'attachment; filename="pfam_result.zip"'
        response.set_cookie('pfam_download', 'done', max_age=60, path='/')
        return response
    else:
        return HttpResponse("Error: Result files were not generated.", status=404)

# ================= 4. 视图函数 (Views) =================

def pfam(request):
    return render(request, 'pfam.html')

def pfam_run(request):
    if request.method == 'POST':
        my_file = request.FILES.get("file1", None)
        structure_keywords = request.POST.get('structure', '')

        if not my_file:
            return HttpResponse("Error: No file uploaded.")

        dir_code = get_random_dir_name()
        
        save_uploaded_file(my_file, dir_code)
        
        run_pfam_scan_logic(dir_code, structure_keywords)
        
        files_to_zip = 'pfam.txt pfam_new.txt'
        return create_zip_response(dir_code, files_to_zip)

    return redirect('pfam')
