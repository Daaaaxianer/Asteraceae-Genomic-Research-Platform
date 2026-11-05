import os
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
# 引入 tools 模块
from .tools import name_set, save_uploaded_file, codonw_run_tools, zip_results 

# 页面渲染视图
def codonw(request):
    return render(request, 'codonw.html')

# 运行分析的主视图
def codonw_run(request):
    if request.method == 'POST':
        # 1. 获取上传的文件
        file = request.FILES.get("file", None)
        if file is None:
            return HttpResponse("No file uploaded", status=400)
        
        # 2. 处理文件名 (用于输出文件的命名)
        # 获取原始文件名（不带后缀）
        original_filename = file.name.rsplit('.', 1)[0]
        
        # 清洗文件名：只保留字母、数字、下划线和连字符
        # 这一步是为了防止文件名中有空格或特殊字符导致 zip 步骤出错
        safe_filename = "".join([c for c in original_filename if c.isalnum() or c in ('-', '_')])
        
        # 如果清洗后为空（例如原文件名全是特殊字符），给一个默认名
        if not safe_filename: 
            safe_filename = "codonw_result"

        # 3. 创建随机工作目录
        folder_id = name_set()
        
        # 4. 保存输入文件
        # 【重要】必须保存为 "1.fasta"，因为 tools.py 里写死了读取这个文件名
        save_uploaded_file(file, folder_id, target_name="1.fasta")

        # 5. 运行分析
        # tools 会根据 safe_filename 生成对应的 .out 和 .blk 文件
        # 例如：test.out, test.blk
        codonw_run_tools(folder_id, safe_filename)

        # 6. 准备压缩
        # 构造一个空格分隔的字符串传给 tools.zip_results
        files_to_zip = f"{safe_filename}.out {safe_filename}.blk"
        zip_path = zip_results(folder_id, files_to_zip)

        # 7. 返回下载
        if zip_path and os.path.exists(zip_path):
            # 打开压缩包并返回
            response = FileResponse(open(zip_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            # 下载时显示的文件名，加上 safe_filename 方便用户区分
            response['Content-Disposition'] = f'attachment; filename="CodonW_{safe_filename}.zip"'
            response.set_cookie('codonw_download', 'done', max_age=60, path='/')
            return response
        else:
            # 失败提示：通常是因为上传了蛋白质序列导致 CodonW 没有任何输出
            return HttpResponse(
                "Analysis failed. Output files are empty.<br>"
                "<b>Potential Cause:</b> You might have uploaded a Protein sequence (amino acids). "
                "CodonW requires a <b>CDS/DNA sequence</b> (A, T, C, G).", 
                status=500
            )
            
    return HttpResponse("Invalid Method", status=405)
