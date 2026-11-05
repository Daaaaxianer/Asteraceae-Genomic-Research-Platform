import os
import time
import uuid
import zipfile
import traceback
from urllib.parse import quote, unquote

from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.conf import settings
from Bio import SeqIO  # 唯一需要的生物学库

# ==========================================
# 1. 基础路径配置
# ==========================================

def get_real_base_dir():
    """获取当前脚本所在的项目根目录"""
    # 假设 views.py 在 app/tools/ 目录下，向上找3层回到根目录
    # 如果你的结构不同，请微调这里。
    # 针对你截图的结构 (QUCHONG/tools/views.py)，根目录应该是 QUCHONG
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current_dir)

# 全局基础路径
BASE_DIR = get_real_base_dir()
FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')

# 确保文件夹存在
if not os.path.exists(FILE_KEEP_DIR):
    os.makedirs(FILE_KEEP_DIR)

print(f"✅ [View] 工作目录已设定: {BASE_DIR}")


# ==========================================
# 2. 核心工具函数 (替代原 tools.py)
# ==========================================

def create_workspace():
    """创建一个唯一的工作目录"""
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    folder_path = os.path.join(FILE_KEEP_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_name, folder_path

def save_uploaded_file(file_obj, folder_path, filename):
    """保存上传的文件"""
    target_path = os.path.join(folder_path, filename)
    with open(target_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    return target_path

def perform_deduplication(work_path):
    """
    【核心功能】替代原有的 quchong_run
    读取 1.fasta -> 去重 -> 写入 new.fasta
    """
    input_file = os.path.join(work_path, '1.fasta')
    output_file = os.path.join(work_path, 'new.fasta')
    
    seen_ids = set()
    
    try:
        # 使用 Biopython 解析并去重
        # encoding='utf-8' 防止中文乱码
        with open(output_file, 'w', encoding='utf-8') as handle:
            # 自动识别格式 (fasta/cds)
            for record in SeqIO.parse(input_file, "fasta"):
                if record.id not in seen_ids:
                    seen_ids.add(record.id)
                    SeqIO.write(record, handle, "fasta")
        return True
    except Exception as e:
        print(f"❌ Deduplication Error: {e}")
        # 如果解析失败，可能是编码问题，尝试忽略错误读取
        traceback.print_exc()
        raise e

def create_zip(folder_path, target_filename):
    """打包结果文件"""
    zip_filename = 'result.zip'
    zip_filepath = os.path.join(folder_path, zip_filename)
    target_file = os.path.join(folder_path, target_filename)

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(target_file):
                zf.write(target_file, arcname=target_filename)
        return zip_filepath
    except Exception as e:
        print(f"Zip Error: {e}")
        return None

# ==========================================
# 3. 视图函数
# ==========================================

def duplicate_removal(request):
    """首页视图 (对应 urls.py 中的 name='quchong_url' 或 index)"""
    return render(request, 'quchong.html')

def duplicate_removal_run(request):
    """
    处理上传 -> 运行去重 -> 直接触发下载
    """
    if request.method != 'POST':
        return redirect('duplicate_removal')

    try:
        file = request.FILES.get("file", None)
        if not file:
            return HttpResponse("No file uploaded.")

        # 1. 创建工作区
        folder_name, folder_path = create_workspace()

        # 2. 保存文件
        save_uploaded_file(file, folder_path, '1.fasta')

        # 3. 运行去重逻辑
        perform_deduplication(folder_path)

        # 4. 打包结果
        zip_path = create_zip(folder_path, 'new.fasta')
        
        if not zip_path:
            return HttpResponse("Error creating zip file.", status=500)

        # ========================================================
        # 【修改重点】：这里不再生成链接跳转 HTML，而是直接返回文件流
        # ========================================================
        
        # 打开刚才生成的 zip 文件
        file_handle = open(zip_path, 'rb')
        
        # 创建 FileResponse 对象
        response = FileResponse(file_handle)
        
        # 设置响应头：attachment 表示以附件形式下载，filename 是用户看到的文件名
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename="BDl_Deduplicated_Result.zip"'
        
        return response

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Error processing file: {str(e)}", status=500)

def file_download(request):
    """文件下载接口"""
    try:
        file_path_encoded = request.GET.get('file', '')
        if not file_path_encoded:
            return HttpResponse("No file specified", status=400)
        
        file_path = unquote(file_path_encoded)
        
        # 安全检查：防止目录遍历攻击，只允许下载 file_keep 下的文件
        if 'file_keep' not in os.path.abspath(file_path):
             return HttpResponse("Access Denied.", status=403)
        
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="BDl_Deduplicated_Result.zip"'
            return response
        else:
            return HttpResponse("File not found.", status=404)
    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Download Error: {e}", status=500)