import os
import random
import string
import shutil
import subprocess
import zipfile  # 引入Python原生压缩库，不再依赖系统命令
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

# ================= 配置区域 =================

# 1. 定义文件存储的绝对路径
BASE_FILE_KEEP_PATH = "/wangjp/Asteraceae/Asteraceae/file_keep"

# 2. 定义 FastTree 软件的绝对路径
FASTTREE_PATH = "/www/tools/soft_tools/FastTree"


# ================= 辅助函数 =================

def get_random_dir_name():
    """
    在 file_keep 中创建一个随机命名的文件夹，并返回文件夹名称和绝对路径
    """
    # 确保根目录存在
    if not os.path.exists(BASE_FILE_KEEP_PATH):
        try:
            os.makedirs(BASE_FILE_KEEP_PATH)
        except OSError as e:
            raise RuntimeError(f"Could not create storage directory {BASE_FILE_KEEP_PATH}: {e}")

    # 生成9位随机数字作为文件夹名
    while True:
        dir_name = ''.join(random.sample(string.digits, 9))
        full_path = os.path.join(BASE_FILE_KEEP_PATH, dir_name)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            return dir_name, full_path

def save_uploaded_file(file_obj, work_dir, rename_to="input.phy"):
    """
    将 Django 上传的文件对象保存到指定目录
    """
    file_path = os.path.join(work_dir, rename_to)
    try:
        with open(file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        return file_path
    except Exception as e:
        raise RuntimeError(f"Could not save the file: {str(e)}")

def run_fasttree_cmd(work_dir, pattern):
    """
    在指定目录下运行 FastTree 命令
    """
    input_file = "input.phy"
    output_file = "output.nwk"
    
    # 检查 FastTree 是否存在
    if not os.path.isfile(FASTTREE_PATH):
        raise RuntimeError(f"FastTree was not found. Check the path: {FASTTREE_PATH}")

    # 构建命令，使用绝对路径
    if pattern == "GTR+CAT":
        # GTR + CAT 模型 (更慢但更准确)
        cmd = f"{FASTTREE_PATH} -gtr -nt {input_file} > {output_file}"
    else:
        # 默认 JTT + CAT 模型 (速度快)
        cmd = f"{FASTTREE_PATH} {input_file} > {output_file}"

    try:
        # 使用 subprocess 运行
        process = subprocess.run(
            cmd, 
            shell=True, 
            cwd=work_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        # 捕获标准错误输出，方便调试
        error_msg = e.stderr.decode(errors='ignore') if e.stderr else str(e)
        raise RuntimeError(f"FastTree failed: {error_msg}")

    # 检查输出文件是否生成
    if not os.path.exists(os.path.join(work_dir, output_file)):
        raise RuntimeError("FastTree finished without generating output.nwk. Check that the input is in MSA format.")

def create_zip_archive(work_dir, target_file="output.nwk"):
    """
    使用 Python zipfile 模块压缩结果文件 (修复 zip 命令失败的问题)
    """
    zip_name = "result.zip"
    zip_path = os.path.join(work_dir, zip_name)
    target_path = os.path.join(work_dir, target_file)
    
    try:
        # 使用 w 模式创建压缩文件，ZIP_DEFLATED 为标准压缩算法
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # write(文件路径, 压缩包内的文件名)
            zf.write(target_path, arcname=target_file)
            
        return zip_path
    except Exception as e:
        print(f"ZIP compression error: {e}")
        return None


# ================= Views 视图函数 =================

def fasttree(request):
    """
    渲染 FastTree 输入页面
    """
    return render(request, 'fasttree.html')

@csrf_exempt
def fasttree_run(request):
    """
    处理表单提交，运行 FastTree 并返回 Zip 文件
    """
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    try:
        # 1. 获取前端数据
        patten = request.POST.get('patten', 'JTT+CAT')
        uploaded_file = request.FILES.get("file1", None)

        if not uploaded_file:
            return HttpResponse("Error: please upload an alignment file (.aln or .fasta).", status=400)

        # 2. 创建唯一的工作目录
        dir_name, work_dir = get_random_dir_name()
        
        # 3. 保存上传的文件
        save_uploaded_file(uploaded_file, work_dir, rename_to="input.phy")
        
        # 4. 运行 FastTree
        run_fasttree_cmd(work_dir, patten)
        
        # 5. 打包结果 (使用 Python zipfile)
        zip_path = create_zip_archive(work_dir, target_file="output.nwk")
        
        # 6. 返回文件下载
        if zip_path and os.path.exists(zip_path):
            response = FileResponse(open(zip_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            # 文件名中加入随机ID防止重名困惑
            response['Content-Disposition'] = f'attachment; filename="fasttree_result_{dir_name}.zip"'
            return response
        else:
            # 如果走到这里，说明 FastTree 成功了，但 Python 压缩失败了
            return HttpResponse("Error: the result file was generated, but ZIP packaging failed. Please contact the administrator.", status=500)

    except Exception as e:
        # 将具体错误打印出来，方便直接在网页看到原因
        print(f"Server Error in fasttree_run: {str(e)}")
        return HttpResponse(f"An error occurred during processing: {str(e)}", status=500)