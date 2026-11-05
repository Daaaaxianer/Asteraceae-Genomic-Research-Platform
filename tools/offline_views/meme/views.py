# -*- coding:utf-8 -*-
import os
import random
import string
import shutil
import zipfile
import subprocess
import platform
from urllib.parse import unquote

from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings

# ==============================================================================
#  配置与全局变量
# ==============================================================================

# 1. 确定基础路径
try:
    BASE_DIR = str(settings.BASE_DIR)
except:
    BASE_DIR = None

if not BASE_DIR:
    current_file_path = os.path.abspath(__file__)
    dir_current = os.path.dirname(current_file_path)     
    dir_parent_1 = os.path.dirname(dir_current)          
    dir_parent_2 = os.path.dirname(dir_parent_1)        
    BASE_DIR = os.path.dirname(dir_parent_2)            

# 2. 定义文件保存路径
FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')

# 打印日志以便调试
print(f"--- [Config] BASE_DIR: {BASE_DIR} ---")
print(f"--- [Config] FILE_KEEP_DIR: {FILE_KEEP_DIR} ---")


# ==============================================================================
#  工具函数 / Helper Functions
# ==============================================================================

def name_set():
    """ 
    创建随机命名的工作目录 (ID)
    """
    c = ''.join(random.sample(string.digits, 9))
    target_dir = os.path.join(FILE_KEEP_DIR, c)
    from api.download_access import create_job_directory
    create_job_directory(target_dir)
    return c

def keep_file(file_obj, c):
    """
    保存上传的文件，并重命名为 1.fasta 供 MEME 使用
    """
    save_path = os.path.join(FILE_KEEP_DIR, c)
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    # 强制重命名为 1.fasta，方便后续命令调用
    full_file_path = os.path.join(save_path, '1.fasta')

    try:
        # 使用 'wb+' 写入文件流
        with open(full_file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
    except Exception as e:
        print(f"Error saving file: {e}")
        raise e

def zip_file(place):
    """
    使用 Python 原生库压缩结果文件
    """
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    zip_filename = 'result.zip'
    zip_path = os.path.join(work_dir, zip_filename)

    # 需要压缩的文件后缀
    target_exts = ('.html', '.png', '.txt', '.xml', '.eps')

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 遍历目录
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    # 排除 zip 本身和输入文件
                    if file == zip_filename or file == '1.fasta':
                        continue
                        
                    # 只压缩特定后缀的结果文件 (或者去掉这个 if 压缩所有)
                    if file.endswith(target_exts) or 'meme' in file:
                        file_abs_path = os.path.join(root, file)
                        # arcname 确保压缩包内部没有多余的层级路径
                        zf.write(file_abs_path, arcname=file)
        return zip_path
    except Exception as e:
        print(f"Zip Error: {str(e)}")
        return None

def meme_run_tools(place, patten, motif, motif_num, minw, maxw):
    """
    执行 MEME 分析命令
    """
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    input_file = '1.fasta'
    
    # 检查输入文件
    if not os.path.exists(os.path.join(work_dir, input_file)):
        raise RuntimeError(f"Input file not found in {work_dir}")

    # MEME 可执行文件路径
    meme_exe = "/www/tools/soft_tools/meme" 

    # 构建命令
    # 【修复重点 1】保留 -prior addone 避免库文件错误
    # 【修复重点 2】使用 -text 模式，避开 template.eps/ceqlogo 崩溃问题
    cmd = [
        meme_exe,
        input_file,
        f"-{str(patten).lower()}", # -protein, -dna
        "-text",                   # <--- 开启纯文本输出，直接打印到标准输出
        "-mod", str(motif),        # zoops, oops, anr
        "-nmotifs", str(motif_num),
        "-minw", str(minw),
        "-maxw", str(maxw),
        "-prior", "addone"         # 必须保留
    ]

    print(f"[MEME Tools] Working Dir: {work_dir}")
    print(f"[MEME Tools] Running: {' '.join(cmd)}")

    try:
        process = subprocess.run(
            cmd,
            cwd=work_dir,
            check=True,
            shell=False,
            stdout=subprocess.PIPE, # 捕获标准输出
            stderr=subprocess.PIPE
        )
        
        # 【修复重点 3】手动将结果写入 meme.txt
        # 因为 -text 模式不会自动创建文件，而是输出到屏幕(stdout)
        output_file_path = os.path.join(work_dir, 'meme.txt')
        with open(output_file_path, 'wb') as f:
            f.write(process.stdout)
            
    except subprocess.CalledProcessError as e:
        error_log = e.stderr.decode(errors='ignore') if e.stderr else "Unknown error"
        stdout_log = e.stdout.decode(errors='ignore') if e.stdout else ""
        
        full_log = f"STDERR: {error_log}\nSTDOUT: {stdout_log}"
        print(f"[MEME Error]: {full_log}")
        
        raise RuntimeError(f"MEME execution failed: {error_log}")
        
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {meme_exe}. Please check path.")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


# ==============================================================================
#  视图函数 / Views
# ==============================================================================

def tools_view(request):
    return render(request, 'tools.html')

def meme_suit(request):
    return render(request, 'meme_suit.html')

def meme_suit_run(request):
    """
    处理 MEME 运行请求的主要视图
    """
    if request.method != 'POST':
        return HttpResponse("Method Not Allowed", status=405)

    # 1. 获取上传文件
    myFile1 = request.FILES.get("file1", None)
    if myFile1 is None:
        return HttpResponse("Error: Please upload a FASTA file.", status=400)

    # 2. 获取并清洗参数
    try:
        patten = request.POST.get('patten', 'protein')
        motif = request.POST.get('motif', 'zoops')
        # 转换为 int 以增加健壮性
        motif_num = int(request.POST.get('motif_num', 3))
        minw = int(request.POST.get('minw', 6))
        maxw = int(request.POST.get('maxw', 50))
    except ValueError:
        return HttpResponse("Error: Invalid numeric parameters.", status=400)

    # 3. 创建工作目录
    c = name_set()

    # 4. 保存文件
    try:
        keep_file(file_obj=myFile1, c=c)
    except Exception:
        return HttpResponse("Error: Failed to save uploaded file.", status=500)

    # 5. 运行 MEME
    try:
        meme_run_tools(
            place=c, 
            patten=patten, 
            motif=motif, 
            motif_num=motif_num, 
            minw=minw, 
            maxw=maxw
        )
    except RuntimeError as e:
        # 捕获已知运行错误并返回给前端
        return HttpResponse(f"Analysis Failed: {str(e)}", status=500)

    # 6. 压缩结果
    zip_path = zip_file(place=c)

    # 7. 返回文件下载流
    if zip_path and os.path.exists(zip_path):
        try:
            file_handle = open(zip_path, 'rb')
            response = FileResponse(file_handle)
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="meme_result_{c}.zip"'
            response.set_cookie('meme_download', 'done', max_age=60, path='/')
            return response
        except Exception as e:
            return HttpResponse(f"Error sending file: {str(e)}", status=500)
    else:
        return HttpResponse("Error: Failed to generate result file.", status=500)

def download_file_view(request):
    """
    通用文件下载视图
    """
    file_path = unquote(request.GET.get('file', ''))
    
    if os.path.exists(file_path):
        try:
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
        except Exception:
            return HttpResponse("Error reading file", status=500)
    else:
        return HttpResponse("File not found", status=404)
