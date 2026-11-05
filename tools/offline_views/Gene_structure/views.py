# tools/views.py

import os
import time
import base64
import uuid
import shutil # 用于删除文件夹
import traceback
import re
import matplotlib
import logging # 用于规范日志

# =========================================================
# 1. 绘图库防崩溃设置 (必须在 import pyplot 之前)
# =========================================================
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings

# 设置日志
logger = logging.getLogger(__name__)

# =========================================================
# 2. 基础配置与路径
# =========================================================
BASE_DIR = str(settings.BASE_DIR)
FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')

if not os.path.exists(FILE_KEEP_DIR):
    os.makedirs(FILE_KEEP_DIR)

# =========================================================
# 3. 辅助函数
# =========================================================

def create_temp_dir():
    """生成唯一的临时工作目录"""
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:8]}"
    folder_path = os.path.join(FILE_KEEP_DIR, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path, folder_name

def save_uploaded_file(file_obj, folder_path):
    """保存上传的文件到指定目录"""
    if not file_obj: 
        return None
    # 简单净化文件名，防止路径遍历攻击
    safe_name = os.path.basename(file_obj.name)
    target_path = os.path.join(folder_path, safe_name)
    
    with open(target_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    return target_path

def normalize_gff_text_line(line):
    """Normalize BOM and escaped tab variants in uploaded example files."""
    if line is None:
        return ""

    normalized = line.lstrip('\ufeff')
    if '\t' not in normalized:
        normalized = normalized.replace('`t', '\t').replace('\\t', '\t')
    return normalized

# =========================================================
# 4. 核心绘图逻辑类
# =========================================================
class GeneStructurePlotter:
    def __init__(self, gff_file_path, chromosome_to_extract, start_position, end_position,
                 colors_file_path, image_size=(1200, 400), gene_height=0.4):
        self.gff_file_path = gff_file_path
        self.chromosome = str(chromosome_to_extract).strip()
        self.start_pos = int(start_position)
        self.end_pos = int(end_position)
        self.colors_file_path = colors_file_path
        self.image_size = image_size
        self.gene_height = gene_height

    def extract_gff_data(self):
        """解析 GFF 文件"""
        gene_dict = {}
        
        if not os.path.exists(self.gff_file_path):
            return gene_dict
            
        with open(self.gff_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = normalize_gff_text_line(line)
                if line.startswith('#') or not line.strip(): 
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) < 7: continue

                seqid = parts[0].strip()
                # 预筛选：染色体不符直接跳过，提升速度
                if seqid != self.chromosome: continue

                try:
                    start = int(parts[3]) if len(parts) >= 9 else int(parts[1])
                    end = int(parts[4]) if len(parts) >= 9 else int(parts[2])
                    
                    # 范围筛选：必须有重叠才保留
                    if end < self.start_pos or start > self.end_pos:
                        continue

                    strand = parts[6] if len(parts) >= 9 else parts[3]
                    feature_type = parts[2].lower() if len(parts) >= 9 else "gene"
                    attributes = parts[8] if len(parts) >= 9 else parts[4]
                    
                    # ID 提取逻辑
                    display_id = "Unknown"
                    # 尝试提取 ID 或 Name
                    id_match = re.search(r'ID=([^;]+)', attributes)
                    name_match = re.search(r'Name=([^;]+)', attributes)
                    
                    if id_match:
                        display_id = id_match.group(1).strip()
                    elif name_match:
                        display_id = name_match.group(1).strip()
                    elif len(parts) == 7:
                        display_id = parts[4].strip() # 简易格式直接取第5列
                    
                    # 过滤掉不需要的特征类型，主要保留 gene 或 mRNA
                    if feature_type not in ['gene', 'mrna', 'transcript']:
                        continue

                    clean_id = re.sub(r'\.[a-zA-Z0-9]+$', '', display_id) # 去除版本号

                    # 存储数据
                    # 逻辑优化：如果ID已存在，且当前是 mRNA，覆盖旧的 gene (因为 mRNA 信息通常更精准)
                    if clean_id in gene_dict:
                        if gene_dict[clean_id]['type'] == 'gene' and feature_type != 'gene':
                            gene_dict[clean_id] = {
                                'start': start, 'end': end, 'strand': strand, 
                                'type': feature_type, 'display_id': clean_id
                            }
                    else:
                        gene_dict[clean_id] = {
                            'start': start, 'end': end, 'strand': strand, 
                            'type': feature_type, 'display_id': clean_id
                        }

                except (ValueError, IndexError):
                    continue
                    
        return gene_dict

    def read_highlight_colors(self):
        """读取高亮文件"""
        colors = {}
        if not self.colors_file_path or not os.path.exists(self.colors_file_path):
            return colors
        
        try:
            with open(self.colors_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.lstrip('\ufeff')
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        gene_id = parts[0].strip()
                        color = parts[1].strip()
                        # 同时存储原始ID和去后缀ID，增加匹配命中率
                        colors[gene_id] = color
                        clean_id = re.sub(r'\.[a-zA-Z0-9]+$', '', gene_id)
                        colors[clean_id] = color
        except Exception:
            pass
        return colors

    def draw(self, output_path):
        genes = self.extract_gff_data()
        colors = self.read_highlight_colors()
        
        # 即使报错也要确保 plt.close 执行
        fig = None
        try:
            dpi = 100
            w_inch = self.image_size[0] / dpi
            h_inch = self.image_size[1] / dpi
            
            fig, ax = plt.subplots(figsize=(w_inch, h_inch), dpi=dpi)

            if not genes:
                ax.text(0.5, 0.5, f"No genes found in region\n{self.chromosome}:{self.start_pos}-{self.end_pos}", 
                        transform=ax.transAxes, ha='center', va='center', color='#e74c3c', fontsize=14)
                ax.axis('off')
                plt.savefig(output_path, format='png', bbox_inches='tight')
                return

            # 绘制基因组基线
            y_base = 0
            # 只画从 start 到 end 的线
            ax.hlines(y_base + self.gene_height/2, self.start_pos, self.end_pos, colors='#ecf0f1', lw=4, zorder=0)

            sorted_genes = sorted(genes.values(), key=lambda x: x['start'])
            
            # 坐标转换参数
            span = self.end_pos - self.start_pos
            if span == 0: span = 1
            bp_per_pixel = span / self.image_size[0]

            # 避让算法变量
            text_levels = [] # 记录每一层最右侧的位置
            
            # --- 标签避让逻辑 (水平文字版 - 2026 Updated) ---
            for g in sorted_genes:
                gid = g['display_id']
                start, end = g['start'], g['end']
                
                # 截断绘制：如果基因超出了显示范围，将其截断在图内
                draw_start = max(start, self.start_pos)
                draw_end = min(end, self.end_pos)
                
                if draw_end <= draw_start: continue

                # 颜色逻辑
                fill_color = colors.get(gid, '#95a5a6') # 默认灰色
                edge_color = '#e67e22' if g['strand'] == '+' else '#3498db'

                # 绘制基因块
                rect = FancyBboxPatch((draw_start, y_base), draw_end - draw_start, self.gene_height,
                                      boxstyle="round,pad=0.02", 
                                      ec=edge_color, fc=fill_color, lw=1.5, zorder=10)
                ax.add_patch(rect)

                # --- 文字布局核心修改开始 ---
                
                # 1. 计算标签中心点
                label_x = draw_start + (draw_end - draw_start)/2
                
                # 2. 重新估算标签宽度 (针对水平文字)
                # 字体大小设为 9，每个字符大约占 0.65 * fontSize 的像素宽度
                # 将像素宽度转换为 bp 宽度，用于防重叠计算
                font_size = 9
                approx_char_width_px = font_size * 0.65 
                text_width_bp = len(gid) * approx_char_width_px * bp_per_pixel
                
                label_left = label_x - text_width_bp/2
                label_right = label_x + text_width_bp/2
                
                # 3. 寻找可用层级 (贪心算法)
                found_level = -1
                # 增加 padding，防止水平文字首尾相接太紧
                padding = text_width_bp * 0.15 
                
                for i, right_edge in enumerate(text_levels):
                    if right_edge + padding < label_left:
                        found_level = i
                        text_levels[i] = label_right
                        break
                
                if found_level == -1:
                    text_levels.append(label_right)
                    found_level = len(text_levels) - 1
                
                # 4. 确定Y坐标
                # level_step 设置为 0.35，保证水平文字上下有足够空隙
                level_step = 0.35
                # 基础高度抬高到 0.25，给第一层文字留出画线空间
                text_y = y_base + self.gene_height + 0.25 + (found_level * level_step)
                
                # 5. 绘制连接线 (强制绘制 - 只要有文字就画线)
                # 虚线从基因块顶部画到文字底部下方一点点
                ax.plot([label_x, label_x], [y_base + self.gene_height, text_y - 0.02], 
                        color='#999999', ls='--', lw=0.8, zorder=5)

                # 6. 绘制文字 (rotation=0 即为水平正向)
                ax.text(label_x, text_y, gid, ha='center', va='bottom', fontsize=font_size, 
                        rotation=10, color='#2c3e50', zorder=20, fontweight='medium')
                
                # --- 文字布局核心修改结束 ---

            # 调整视图
            max_level = len(text_levels) if text_levels else 0
            # 动态调整顶部空间
            top_lim = 1.0 + (max_level * 0.35)
            
            ax.set_xlim(self.start_pos, self.end_pos)
            ax.set_ylim(-0.2, top_lim)
            
            # 美化坐标轴
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.get_yaxis().set_visible(False)
            
            ax.set_xlabel(f"Chromosome {self.chromosome} Position (bp)", fontsize=11, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(output_path, format='png', transparent=True)
            
        finally:
            # 必须关闭 figure 释放内存
            if fig:
                plt.close(fig)

# =========================================================
# 5. 视图入口
# =========================================================

def draw_gene_structure(request):
    """GET请求返回页面"""
    return render(request, 'draw_gene_structure.html')

def draw_gene_structure_run(request):
    """POST请求处理数据"""
    if request.method != 'POST':
        return draw_gene_structure(request)
    
    # 初始化变量，确保 finally 块能访问
    temp_dir_path = None 
    
    try:
        # 1. 获取输入
        gff_file = request.FILES.get("gff_file")
        highlight_file = request.FILES.get("highlight_file") # 可选
        chrom_id = request.POST.get('chromosome_position')
        start_val = request.POST.get('start')
        end_val = request.POST.get('termination')

        # 2. 基础校验
        if not gff_file or not chrom_id or not start_val or not end_val:
            return HttpResponse("Missing required fields.", status=400)
            
        try:
            start_pos = int(start_val)
            end_pos = int(end_val)
            if start_pos >= end_pos:
                return HttpResponse("Start position must be smaller than End position.", status=400)
        except ValueError:
            return HttpResponse("Positions must be integers.", status=400)

        # 3. 创建临时环境
        temp_dir_path, _ = create_temp_dir()
        
        # 4. 保存文件
        gff_path = save_uploaded_file(gff_file, temp_dir_path)
        hl_path = save_uploaded_file(highlight_file, temp_dir_path) if highlight_file else None
        output_png_path = os.path.join(temp_dir_path, 'result.png')

        # 5. 执行绘图
        plotter = GeneStructurePlotter(
            gff_file_path=gff_path,
            chromosome_to_extract=chrom_id,
            start_position=start_pos,
            end_position=end_pos,
            colors_file_path=hl_path
        )
        plotter.draw(output_png_path)

        # 6. 读取结果并转 Base64
        if os.path.exists(output_png_path):
            with open(output_png_path, 'rb') as f:
                img_data = f.read()
                png_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # 返回结果页面
            return render(request, 'draw_gene_structure.html', {'png_content': png_base64})
        else:
            return HttpResponse("Failed to generate image.", status=500)

    except Exception as e:
        logger.error(f"Error in draw_gene_structure_run: {traceback.format_exc()}")
        return HttpResponse(f"Server Error: {str(e)}", status=500)
        
    finally:
        # 7. 【关键】清理临时文件
        # 无论成功失败，都删除这个请求创建的临时文件夹
        if temp_dir_path and os.path.exists(temp_dir_path):
            try:
                shutil.rmtree(temp_dir_path)
            except OSError as e:
                logger.error(f"Failed to delete temp dir {temp_dir_path}: {e}")

def extract_chromosomes(request):
    """扫描 GFF 文件获取染色体列表"""
    if request.method == 'POST' and request.FILES.get('gff_file'):
        try:
            gff_file = request.FILES['gff_file']
            chromosomes = set()
            
            # 限制读取行数或字节数，防止文件过大导致超时
            # 这里简单处理：流式读取
            for line in gff_file:
                try:
                    line_str = normalize_gff_text_line(line.decode('utf-8', errors='ignore'))
                    if line_str.startswith('#') or not line_str.strip():
                        continue
                    parts = line_str.split('\t')
                    if len(parts) >= 5: 
                        chrom = parts[0].strip()
                        # 过滤掉显然不是染色体的奇怪ID (可选)
                        if chrom and not chrom.startswith('#') and len(chrom) < 50: 
                            chromosomes.add(chrom)
                except: 
                    continue
            
            # 自然排序 (1, 2, 10 而不是 1, 10, 2)
            def natural_keys(text):
                return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]
                
            sorted_chroms = sorted(list(chromosomes), key=natural_keys)
            
            return JsonResponse({'status': 'success', 'chromosomes': sorted_chroms})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})
