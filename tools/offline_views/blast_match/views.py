import os
import zipfile
import io
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from .tools import name_set, keep_file, blast_match_run_tools

# 获取当前工作目录
path_get = os.getcwd()

def blast_match(request):
    """渲染 Blast Match 页面"""
    return render(request, 'blast_match.html')

def zip_file_response(place, filenames, zip_name="result.zip"):
    """
    使用 Python zipfile 模块打包文件并返回 FileResponse
    :param place: 随机文件夹名称 (在 file_keep 下)
    :param filenames: 需要打包的文件名列表 (字符串列表 或 空格分隔的字符串)
    :param zip_name: 下载时的压缩包文件名
    """
    base_dir = os.path.join(path_get, 'file_keep', place)
    
    # 如果 filenames 是字符串，按空格分割
    if isinstance(filenames, str):
        filenames = filenames.split()

    # 创建一个内存中的 BytesIO 对象，或者直接生成临时文件
    # 这里为了简单稳妥，我们直接在磁盘生成 zip，然后读取返回
    zip_file_path = os.path.join(base_dir, zip_name)

    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for fname in filenames:
                file_path = os.path.join(base_dir, fname)
                if os.path.exists(file_path):
                    # arcname 是在压缩包内显示的文件名，避免包含绝对路径
                    zipf.write(file_path, arcname=fname)
                else:
                    print(f"Warning: File not found {file_path}")
        
        # 返回文件流
        if os.path.exists(zip_file_path):
            response = FileResponse(open(zip_file_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="{zip_name}"'
            response.set_cookie('blast_match_download', 'done', max_age=60, path='/')
            return response
        else:
            return HttpResponse("Error: Zip file creation failed.", status=500)

    except Exception as e:
        return HttpResponse(f"Error packing files: {str(e)}", status=500)


def blast_match_run(request):
    """处理 Blast Match 表单提交"""
    if request.method == 'POST':
        # 1. 获取参数
        patten = request.POST.get("patten", "blastp")
        species_data = request.POST.get("species_data", None)
        myFile1 = request.FILES.get("file1", None)
        
        e_value = request.POST.get('e_value', '1e-5')
        sco = request.POST.get('score_1', '0')
        iden = request.POST.get('identity_1', '0')
        
        # 判断是核酸还是蛋白
        nucl_or_prot = "prot" if patten == 'blastp' else "nucl"
        
        # 2. 验证文件
        if myFile1 is None:
            return render(request, 'blast_match.html', {"error": "Please upload a file."})
        
        # 3. 创建临时目录并保存文件
        c = name_set()  # 在 tools.py 中定义
        myFile1.name = '1.fasta' # 重命名上传的文件
        keep_file(na=myFile1, c=c) # 在 tools.py 中定义
        
        # 4. 运行 Blast 工具链
        try:
            blast_match_run_tools(
                place=c, 
                patten=patten, 
                species_data=species_data, 
                e=e_value, 
                score=sco, 
                identity=iden, 
                nucl_or_prot=nucl_or_prot
            )
        except Exception as e:
            # 运行出错时的简单处理
            return HttpResponse(f"Error running blast: {str(e)}")

        # 5. 打包并返回结果
        # 需要打包的文件列表
        target_files = ["result_2.fasta", "sequence.txt", "result.txt"] 
        return zip_file_response(c, target_files)
    
    return render(request, 'blast_match.html')
