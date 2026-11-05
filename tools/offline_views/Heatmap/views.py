# tools/offline_views/Heatmap/views.py
import os
import time
import base64
import traceback
import numpy as np
import pandas as pd

# --- 绘图库设置 ---
import matplotlib
# 强制使用非交互式后端，防止在后台运行时崩溃导致"拒绝连接"
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.conf import settings
from urllib.parse import quote, unquote

# 1. 自动获取根目录
def get_real_base_dir():
    # 当前文件: /tools/offline_views/Heatmap/views.py
    # 需要回退 4 层才能到达存放 file_keep 的根目录
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

path_get = get_real_base_dir()

# 确保文件夹存在
for d in ['file_keep', os.path.join('file_keep', 'species_data')]:
    os.makedirs(os.path.join(path_get, d), exist_ok=True)

# 工具函数：生成唯一文件夹名
def name_set():
    import uuid
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    folder_path = os.path.join(path_get, 'file_keep', folder_name)
    from api.download_access import create_job_directory
    create_job_directory(folder_path)
    return folder_name

# 工具函数：保存上传文件
def keep_file(na, c):
    if not na: return None
    target_dir = os.path.join(path_get, 'file_keep', c)
    file_path = os.path.join(target_dir, na.name)
    with open(file_path, 'wb+') as destination:
        for chunk in na.chunks():
            destination.write(chunk)
    return file_path

# --- 视图函数 ---

# 1. 渲染页面
def draw_heatmap(request):
    return render(request, 'draw_heatmap.html')

# 2. 执行绘图逻辑
def draw_heatmap_run(request):
    try:
        # --- 1. 获取参数 ---
        file = request.FILES.get("file", None)
        
        # 获取复选框状态 (选中为 'on', 否则 None)
        log2 = request.POST.get('log2') == 'on'
        column = request.POST.get('column') == 'on'
        row = request.POST.get('row') == 'on'
        
        # 颜色和尺寸
        color1 = request.POST.get('color1', '#D41B03')
        color2 = request.POST.get('color2', '#FEF9FA')
        color3 = request.POST.get('color3', '#3229D0')
        
        try:
            width = int(request.POST.get('width', 8))
            height = int(request.POST.get('height', 10))
        except ValueError:
            width, height = 8, 10

        if not file:
            return render(request, 'draw_heatmap.html', {"error": "Please upload a file."})

        # --- 2. 保存文件 ---
        c = name_set()
        file_path = keep_file(file, c)

        # --- 3. 读取数据 ---
        data = None
        read_error = None
        
        # 尝试列表：(分隔符, 编码)
        try_options = [
            ('\t', 'utf-8'),  # 标准 TSV/TXT
            (',', 'utf-8'),   # 标准 CSV
            ('\t', 'gbk'),    # Windows Excel 导出 TXT (中文环境)
            (',', 'gbk'),     # Windows Excel 导出 CSV (中文环境)
        ]

        for sep, encoding in try_options:
            try:
                temp_data = pd.read_csv(file_path, sep=sep, index_col=0, encoding=encoding)
                # 简单的校验：如果读出来只有0列，可能是分隔符错了
                if temp_data.shape[1] < 1: 
                    continue
                data = temp_data
                break 
            except Exception as e:
                read_error = e
                continue
        
        if data is None:
            raise Exception(f"Could not read the file. Check its format. Last error: {read_error}")

        # --- 4. 数据清洗 (增强版) ---
        # 4.1 替换字符串 'Na' 为 NaN
        data = data.replace("Na", np.nan)
        
        # 4.2 强制将所有列转换为数字，遇到无法转换的(如字符串)变为NaN
        data = data.apply(pd.to_numeric, errors='coerce')

        # --- 5. 数据处理 (Log2) ---
        if log2:
            data = data + 1
            data = np.log2(data)
            # 替换 log 产生的无限值 (-inf, inf) 为 NaN
            data = data.replace([np.inf, -np.inf], np.nan)

        # 4.3 彻底删除含有 NaN 的行
        data = data.dropna(axis=0)

        # --- 6. 绘图前检查 (防止报错的关键步骤) ---
        if data.empty:
            raise Exception("No data remains after processing. Check that the input contains valid numbers and is not mostly empty.")
        
        # 如果数据量太少(少于2行或2列)，强制关闭聚类，防止 Scipy 报错
        if data.shape[0] < 2:
            row = False
        if data.shape[1] < 2:
            column = False

        # --- 7. 绘图 (Seaborn) ---
        cmap = sns.blend_palette([color1, color2, color3], as_cmap=True)
        
        clustermap = sns.clustermap(
            data, 
            cmap=cmap, 
            linewidths=0.0,
            linecolor='gray',
            method='average', 
            metric='euclidean',
            col_cluster=column, 
            row_cluster=row, 
            figsize=(width, height)
        )
        
        clustermap.fig.set_dpi(300)

        # --- 8. 保存图片 ---
        input_filename = os.path.splitext(file.name)[0]
        output_filename = f"{input_filename}_heatmap.png"
        output_file = os.path.join(path_get, 'file_keep', c, output_filename)
        
        clustermap.savefig(output_file)
        plt.close('all') 

        # --- 9. 返回结果 ---
        with open(output_file, 'rb') as f:
            png_content = base64.b64encode(f.read()).decode('utf-8')
            
        return render(request, 'draw_heatmap.html', {'png_content': png_content})

    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"<h3>Analysis failed</h3><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>")

# 文件下载 (保留接口)
def file_download(request):
    try:
        file_path_encoded = request.GET.get('file', '')
        if not file_path_encoded:
            return HttpResponse("No file specified", status=400)
        
        file_path = unquote(file_path_encoded)
        
        # 安全检查
        if 'file_keep' not in os.path.abspath(file_path):
             return HttpResponse("Access Denied", status=403)
        
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
        else:
            return HttpResponse("File not found", status=404)
    except Exception as e:
        return HttpResponse(f"Download Error: {e}", status=500)