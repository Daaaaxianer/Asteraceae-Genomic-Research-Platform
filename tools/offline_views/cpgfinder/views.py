import os
import zipfile
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings
# 假设你的 tools.py 在当前应用目录下
from . import tools 

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def tools_page(request):
    return render(request, 'tools.html')

def cpgfinder(request):
    return render(request, 'cpgfinder.html')

def cpgfinder_run(request):
    if request.method != 'POST':
        return render(request, 'cpgfinder.html')

    # 1. 获取上传的文件
    myFile1 = request.FILES.get("file1", None)
    
    # 2. 获取参数并进行类型转换 (增加健壮性)
    try:
        island = int(request.POST.get('island', 200))
        cg_percent = int(request.POST.get('cg_percent', 50))
        gc_ratio = float(request.POST.get('gc_ratio', 0.6))
    except ValueError:
        return HttpResponse("Invalid parameters. Please enter valid numbers.", status=400)

    if myFile1 is None:
        return HttpResponse("Please upload a file.", status=400)

    try:
        # 3. 创建随机工作目录
        c = tools.name_set()
        
        # 4. 保存上传的文件
        # 【关键修改】：接收 keep_file 返回的 cleaned_filename
        # 因为 tools.keep_file 会把空格替换为下划线，必须用这个新名字去后续步骤找文件
        cleaned_filename = tools.keep_file(myFile1, c)

        # 5. 运行 Cpgfinder 工具
        # 【关键修改】：传入 cleaned_filename
        tools.run_cpgfinder_process(
            place=c, 
            island=island, 
            cg_percent=cg_percent, 
            gc_ratio=gc_ratio, 
            filename=cleaned_filename 
        )

        # 6. 打包结果并返回下载
        # 结果文件名为 cpgfinder_result.txt
        zip_file_path = tools.create_zip_archive(c, 'cpgfinder_result.txt')
        
        if zip_file_path and os.path.exists(zip_file_path):
            # 打开文件流
            response = FileResponse(open(zip_file_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            # 设置下载文件名
            response['Content-Disposition'] = f'attachment; filename="cpgfinder_result_{c}.zip"'
            response.set_cookie('cpgfinder_download', 'done', max_age=60, path='/')
            return response
        else:
            # 可能是工具运行了但没有找到 CpG 岛，导致结果文件为空或未生成
            return HttpResponse("The analysis finished, but no result file was generated. No CpG islands may have been predicted.", status=200)

    except Exception as e:
        print(f"Error processing cpgfinder: {e}")
        # 将具体错误返回给前端，方便调试
        return HttpResponse(f"An error occurred during processing: {str(e)}", status=500)
