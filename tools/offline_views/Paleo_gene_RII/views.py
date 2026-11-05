# Written by Yu Zijian
# Refactored for Offline Desktop App - Direct Download Version

import os
import time
import uuid
import glob
import traceback
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.utils.encoding import escape_uri_path # 用于处理下载文件名的中文乱码

# 尝试导入同级目录下的 tools 模块
try:
    from .tools import zu_loss_run_tools
except ImportError:
    print("❌ Error: tools.py not found or circular import.")
    zu_loss_run_tools = None

# ✅ 获取项目根目录
BASE_DIR = str(settings.BASE_DIR)

# ✅ file_keep 位于根目录下
FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')

# 确保目录存在
if not os.path.exists(FILE_KEEP_DIR):
    try:
        os.makedirs(FILE_KEEP_DIR)
        print(f"✅ [View] Created file_keep at: {FILE_KEEP_DIR}")
    except OSError as e:
        print(f"❌ [View] Failed to create file_keep: {e}")

print(f"✅ [View] Work Dir: {BASE_DIR}")
print(f"✅ [View] File Keep Dir: {FILE_KEEP_DIR}")

# ================= Helper Functions =================

def name_set():
    """生成唯一工作目录"""
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    folder_path = os.path.join(FILE_KEEP_DIR, folder_name)
    from api.download_access import create_job_directory
    create_job_directory(folder_path)
    return folder_name, folder_path

# ================= Main Views =================

def index(request):
    """主页视图"""
    return render(request, 'zu_loss.html')

def zu_loss_run(request):
    """
    执行 Gene Loss 分析并直接触发下载
    """
    if request.method == 'POST':
        try:
            # 1. 获取上传的文件
            mc_file = request.FILES.get("mc_file")
            
            if not mc_file:
                return HttpResponse("Error: No file uploaded.", status=400)

            # 2. 创建独立工作区
            task_id, task_path = name_set()
            print(f"📂 [View] Created task folder: {task_path}")
            
            # 3. 保存文件
            file_path = os.path.join(task_path, mc_file.name)
            with open(file_path, 'wb+') as f:
                for chunk in mc_file.chunks():
                    f.write(chunk)

            # 4. 调用业务逻辑
            if zu_loss_run_tools:
                print(f"▶ Running task: {task_id}")
                # 如果 lost.py 报错 (exit code != 0)，tools.py 会抛出 RuntimeError
                zu_loss_run_tools(place=task_id) 
            else:
                return HttpResponse("Backend Logic Error: tools module missing.", status=500)

            # 5. 查找生成的 output 文件
            output_dir = os.path.join(task_path, 'output')
            
            # 【关键修改】优先匹配标准结果文件 *_lost.txt
            result_files = glob.glob(os.path.join(output_dir, "*_lost.txt"))
            
            # 如果没找到标准结果，尝试找所有 txt，但必须排除 debug_log.txt
            if not result_files:
                all_txts = glob.glob(os.path.join(output_dir, "*.txt"))
                result_files = [f for f in all_txts if "debug_log.txt" not in os.path.basename(f)]

            if result_files:
                target_file = result_files[0]
                filename = os.path.basename(target_file)
                
                # 6. 直接返回文件流，浏览器会自动下载
                # 使用 'rb' 模式读取二进制流
                response = FileResponse(open(target_file, 'rb'), as_attachment=True)
                response.set_cookie('zu_loss_download', 'done', max_age=60, path='/')
                
                # 处理文件名中的特殊字符（防止中文乱码）
                response['Content-Disposition'] = f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
                
                print(f"✅ Download triggered for: {filename}")
                return response
            else:
                # 尝试读取日志以告知用户发生了什么
                log_path = os.path.join(output_dir, 'debug_log.txt')
                error_detail = ""
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8') as lf:
                        # 读取最后几行日志
                        lines = lf.readlines()[-5:]
                        error_detail = "\nLast Log:\n" + "".join(lines)

                return HttpResponse(f"Analysis finished, but no result file found.\n{error_detail}", status=404)

        except RuntimeError as e:
            # 捕获 subprocess 执行失败
            return HttpResponse(f"Analysis Script Failed:\n{str(e)}", status=500)
            
        except Exception as e:
            traceback.print_exc()
            return HttpResponse(f"System Error: {str(e)}", status=500)
    
    return HttpResponse("Method not allowed", status=405)
