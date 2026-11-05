# -*- coding:utf-8 -*-
import configparser
import matplotlib
import sys

# 【强制修正】必须在导入 pyplot 之前设置 Agg 后端
# 这样可以避免在没有图形界面的服务器(如 Linux/Django)上报错
matplotlib.use('Agg') 

from matplotlib.pyplot import *
from numpy import *
import numpy as np
from functools import reduce 
from operator import add 

# 【字体修正】
# 添加 DejaVu Sans 作为回退字体，确保 Linux 服务器能正常显示文字
try:
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False
except:
    pass

def load_conf(file, section):
    """读取配置文件"""
    conf = configparser.ConfigParser()
    try:
        conf.read(file, encoding='utf-8') 
        if conf.has_section(section):
            return conf.items(section)
        else:
            return []
    except Exception as e:
        print(f"Warning: Failed to load config {file}: {e}")
        return []

# --- 贝塞尔曲线计算 ---
def calculate_coef(p0, p1, p2, p3):
    c = 3*(p1 - p0)
    b = 3*(p2 - p1) - c
    a = p3 - p0 - c - b
    return c, b, a

def Bezier(plist, t):
    p0, p1, p2, p3 = plist
    c, b, a = calculate_coef(p0, p1, p2, p3)
    tsquared = t**2
    tcubic = tsquared*t
    return a*tcubic + b*tsquared + c*t + p0

# --- 全局常量 ---
GAP_RATIO = 4
radius_a, radius_b = .33, .335
sm_radius = (radius_b - radius_a) / 2
blocklength = 0.01  
blockthick = 0.007
shiftratio = 1.1

# --- 数据处理函数 ---
def get_species_and_chr(spelist):
    """处理物种列表"""
    if not spelist: return [], {}
    # 直接信任传入的列表，不再进行复杂的字符串解析
    specieslist = list(set([str(s) for s in spelist]))
    return specieslist, {}

def get_chr_lenth(spelist, fpchrolen, iscompletegenome):
    """
    读取染色体长度文件 (Lens file)
    """
    chro2len = {}
    labels = []
    
    # 确保文件指针在开头
    if hasattr(fpchrolen, 'seek'): fpchrolen.seek(0)
    
    lines = fpchrolen.readlines()
    if not lines:
        print("❌ Error: Lens file is empty!")
        return {}, []

    for row in lines:
        parts = row.strip().split() # 兼容空格和Tab分割
        if len(parts) < 2: continue
        
        chro = parts[0]
        try:
            length = int(parts[1])
        except ValueError:
            continue
            
        # 【关键修改】只要文件里有，就读进来，不再过滤。
        # 这解决了 views.py 强制重命名导致的匹配失败问题。
        chro2len[chro] = length
        labels.append(chro)
            
    if not chro2len:
        print(f"❌ Error: No valid chromosome length found in file.")
        
    return chro2len, labels

def input_gff(fpgff):
    """
    读取基因位置信息 (GFF file)
    格式: chr gene start end ...
    """
    gene2pos = {}
    gene2chain = {}
    gene_labels = {}
    
    if hasattr(fpgff, 'seek'): fpgff.seek(0)
    
    for row in fpgff:
        if not row.strip() or row.startswith('#'): continue
        parts = row.strip().split()
        if len(parts) < 4: continue

        ch = parts[0]
        gene = parts[1]
        try:
            start = int(parts[2])
            end = int(parts[3])
        except ValueError:
            continue

        gene2pos[gene] = start
        diff = end - start
        
        # 计算链方向
        if diff != 0:
            gene2chain[gene] = int(diff / abs(diff))
        else:
            gene2chain[gene] = 1
            
        gene_labels[gene] = ch
        
    fpgff.close()
    return gene2pos, gene2chain, gene_labels

def input_ka_ks(fpgenefamilyinf, genelabels):
    """
    读取 Ks/Ka 文件
    格式: Gene1 Gene2 [Optional] Ks
    """
    genepair2Ks = {}
    genes = []
    
    if hasattr(fpgenefamilyinf, 'seek'): fpgenefamilyinf.seek(0)

    for row in fpgenefamilyinf:
        parts = row.strip().split()
        if len(parts) < 3: continue
        
        gene1, gene2 = parts[0], parts[1]
        
        # 尝试解析 Ks 值，适配不同列数
        Ks = 0.0
        try:
            if len(parts) >= 4:
                Ks = float(parts[3])
            else:
                Ks = float(parts[2]) 
        except ValueError:
            continue

        # 标准化基因对 key
        if gene1 < gene2:
            genepair = gene1 + " " + gene2
        else:
            genepair = gene2 + " " + gene1
        
        # 只有当两个基因都在 GFF 文件中存在位置信息时才记录
        if gene1 in genelabels and gene2 in genelabels:
            genepair2Ks[genepair] = Ks
            if gene1 not in genes: genes.append(gene1)
            if gene2 not in genes: genes.append(gene2)
            
    fpgenefamilyinf.close()
    return genes, genepair2Ks

# --- 绘图辅助 ---
def rad_to_coord(angle, radius):
    return radius * cos(angle), radius * sin(angle)

def to_deg(bp, total):
    return bp * 360. / total if total != 0 else 0

def to_radian(bp, total):
    return radians(bp * 360. / total) if total != 0 else 0

def plot_arc(start, stop, radius):
    if start >= stop: return 
    t = arange(start, stop, pi/720.)
    x, y = radius * cos(t), radius * sin(t)
    plot(x, y, "k-", alpha=.5, lw=0.5)

def plot_cap(angle, clockwise=True, radius=sm_radius):
    if clockwise: 
        t = arange(angle, angle+pi, pi/30.)
    else: 
        t = arange(angle, angle-pi, -pi/30.)
    x, y = radius * cos(t), radius * sin(t)
    middle_r = (radius_a + radius_b) / 2
    x, y = x + middle_r * cos(angle), y + middle_r * sin(angle)
    plot(x, y, "k-", alpha=.5, lw=0.5)

def plot_arc_block1(start, radius, col):
    t = arange(start, start + blocklength, pi/720.)
    x, y = radius * cos(t), radius * sin(t)
    plot(x, y, "-", alpha=1, color=col, lw=4)

def plot_arc_block2(start, radius, col):
    t = arange(start, start + blocklength, pi/720.)
    x, y = radius * cos(t), radius * sin(t)
    plot(x, y, "-", alpha=1, color=col, lw=1.5)

def sort_gene(genes, gene2pos, start_list, labels, genelabels):
    """
    根据基因在基因组上的绝对位置进行排序
    """
    valid_genes = []
    for g in genes:
        if g in genelabels and g in gene2pos:
            ch = genelabels[g]
            if ch in labels:
                valid_genes.append(g)
    
    def get_sort_key(g):
        ch = genelabels[g]
        # 找到染色体在列表中的索引
        if ch in labels:
            idx = labels.index(ch)
            # 绝对位置 = 基因相对位置 + 该染色体起始偏移量
            abs_pos = gene2pos[g] + start_list[idx]
            return abs_pos
        return 0

    valid_genes.sort(key=get_sort_key)
    return valid_genes