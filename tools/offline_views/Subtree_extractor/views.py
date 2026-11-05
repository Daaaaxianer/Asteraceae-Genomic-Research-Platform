import os
import random
import string
import zipfile
import traceback
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from ete3 import Tree  # 核心依赖

# ==========================================
# 1. 基础配置
# ==========================================
BASE_DIR = settings.BASE_DIR
FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')

# ==========================================
# 2. 视图函数 (Django Views)
# ==========================================

def subtree_extractor(request):
    """首页渲染"""
    return render(request, 'subtree_extractor.html')

def subtree_extractor_run(request):
    """
    执行主逻辑：上传 -> 处理 -> 打包下载
    """
    # 1. 获取上传文件
    myFile1 = request.FILES.get('file1', None) # 树文件
    myFile2 = request.FILES.get('file2', None) # 列表文件

    if myFile1 is None or myFile2 is None:
        return HttpResponse("Error: Please upload both files.", status=400)

    try:
        # 2. 创建随机工作目录
        c = name_set()
        work_dir = os.path.join(FILE_KEEP_DIR, c)
        print(f"--- [DEBUG] Working Directory: {work_dir} ---")

        # 3. 保存文件
        # 定义完整路径
        tree_path = os.path.join(work_dir, 'ty.newick')
        list_path = os.path.join(work_dir, 'species.txt')
        output_path = os.path.join(work_dir, 'result_subtree.newick')

        save_file(myFile1, tree_path)
        save_file(myFile2, list_path)
        print("--- [DEBUG] Files saved successfully ---")

        # 4. 调用核心处理逻辑 (直接调用本文件内的函数)
        print("--- [DEBUG] Starting pruning process... ---")
        prune_tree_by_taxa(tree_path, list_path, output_path)
        print("--- [DEBUG] Pruning finished ---")

        # 5. 打包结果并返回
        response = zip_and_download(c, 'result_subtree.newick')
        response.set_cookie('subtree_extractor_download', 'done', max_age=60, path='/')
        return response

    except Exception as e:
        # 错误处理：打印堆栈并显示在网页上
        error_details = traceback.format_exc()
        print("❌ [ERROR] Exception occurred:")
        print(error_details)
        
        html_error = f"""
        <html>
        <head><title>Processing Error</title></head>
        <body style="font-family: Consolas, monospace; padding: 20px; background: #fff0f0;">
            <h2 style="color: #d32f2f;">Processing Failed</h2>
            <p><strong>Error Type:</strong> {str(e)}</p>
            <hr>
            <h3>Detailed Traceback:</h3>
            <div style="background: #333; color: #fff; padding: 15px; border-radius: 5px; overflow: auto; white-space: pre-wrap;">
{error_details}
            </div>
            <p style="margin-top: 20px; color: #666;">Please check the error message above to identify the issue.</p>
        </body>
        </html>
        """
        return HttpResponse(html_error, status=500)

# ==========================================
# 3. 核心业务逻辑 (Core Logic)
# ==========================================

def prune_tree_by_taxa(tree_path, list_path, output_path):
    """
    核心算法：根据物种列表修剪进化树
    """
    # --- A. 读取并清洗目标物种列表 ---
    target_species = []
    try:
        with open(list_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                # 【清洗逻辑】只取第一列，去除 Tab、空格后的内容 (如 "SpeciesA\t123")
                clean_name = line.split('\t')[0].split(' ')[0]
                # 去除引号
                clean_name = clean_name.replace('"', '').replace("'", "")
                
                if clean_name:
                    target_species.append(clean_name)
                    
        print(f"--- [Logic] Loaded {len(target_species)} target species from list.")
    except Exception as e:
        raise Exception(f"Failed to read species list: {str(e)}")

    if not target_species:
        raise Exception("Species list is empty. Please check your text file.")

    # --- B. 尝试加载进化树 (自动识别格式) ---
    formats_to_try = [1, 0, 2, 3, 4, 5, 8, 9]
    t = None
    last_error = ""

    for fmt in formats_to_try:
        try:
            t = Tree(tree_path, format=fmt)
            print(f"--- [Logic] Tree loaded successfully using format={fmt} ---")
            break
        except Exception as e:
            last_error = str(e)
            continue
    
    if t is None:
        raise Exception(f"Could not parse tree file. Not a valid Newick format. Last error: {last_error}")
    
    # --- C. 计算交集与验证 ---
    tree_leaves = set([leaf.name for leaf in t])
    target_set = set(target_species)
    valid_species = list(target_set & tree_leaves)
    
    print(f"--- [Logic] Found {len(valid_species)} matching species. ---")
    
    if not valid_species:
        # 调试信息：对比前5个名字
        sample_tree = list(tree_leaves)[:5]
        sample_list = list(target_set)[:5]
        raise Exception(
            f"No matching species found!\n"
            f"  - Tree examples: {sample_tree}\n"
            f"  - List examples: {sample_list}\n"
            "Please check for spelling differences (spaces vs underscores, etc)."
        )
        
    # --- D. 执行剪枝 ---
    try:
        t.prune(valid_species, preserve_branch_length=True)
        t.write(outfile=output_path, format=1)
        print("--- [Logic] Result written successfully. ---")
    except Exception as e:
        raise Exception(f"Pruning operation failed: {str(e)}")

# ==========================================
# 4. 辅助工具函数 (Utilities)
# ==========================================

def name_set():
    """创建随机文件夹"""
    if not os.path.exists(FILE_KEEP_DIR):
        os.makedirs(FILE_KEEP_DIR)
    c = ''.join(random.sample(string.digits + string.ascii_lowercase, 9))
    target_dir = os.path.join(FILE_KEEP_DIR, c)
    from api.download_access import create_job_directory
    create_job_directory(target_dir)
    return c

def save_file(file_obj, file_path):
    """保存上传文件"""
    with open(file_path, 'wb+') as f:
        for chunk in file_obj.chunks():
            f.write(chunk)

def zip_and_download(place, target_filename):
    """压缩并返回下载流"""
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    zip_path = os.path.join(work_dir, 'result.zip')
    target_file_path = os.path.join(work_dir, target_filename)

    if not os.path.exists(target_file_path):
        raise FileNotFoundError(f"Output file '{target_filename}' not found.")

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(target_file_path, arcname=target_filename)
    except Exception as e:
        raise Exception(f"Failed to create ZIP: {str(e)}")

    return FileResponse(open(zip_path, 'rb'), as_attachment=True, filename='result.zip')
