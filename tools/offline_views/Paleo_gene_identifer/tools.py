#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import sys
import shutil
import traceback
import re
import uuid

# ==========================================
# 绘图后端设置
# ==========================================
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

# ==========================================
# Django 兼容层
# ==========================================
try:
    from django.shortcuts import render
    from django.http import HttpResponse
except ImportError:
    def render(*args, **kwargs): return "Render Placeholder"
    def HttpResponse(*args, **kwargs): return "HttpResponse Placeholder"

# ==========================================
# 路径配置
# ==========================================
def get_project_root():
    current_file = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(current_file))

PATH_ROOT = get_project_root()
FILE_KEEP_DIR = os.path.join(PATH_ROOT, 'file_keep')
if not os.path.exists(FILE_KEEP_DIR): os.makedirs(FILE_KEEP_DIR)

# =========================================================
# 工具函数：ID 清洗
# =========================================================
def clean_id(gid):
    """移除基因ID的后缀 (如 .1, -t1)，确保匹配"""
    if not gid: return ""
    # 移除 . 或 - 之后的内容，但保留基因名前缀
    return re.split(r'[.-]', gid)[0].strip()

# =========================================================
# STEP 1: 生成坐标文件 (Py版 1.tran.position.py)
# =========================================================
def py_tran_position(species1, species2, work_dir):
    """生成 .corr.txt (支持 .lens + .txt 输入)"""
    print(f"[Step 1] Generating coordinate mapping...")
    
    # 尝试多种可能的输入文件名
    lens1 = os.path.join(work_dir, f"{species1}.lens")
    lens2 = os.path.join(work_dir, f"{species2}.lens")
    pos_file_1 = os.path.join(work_dir, f"{species1}_{species2}.txt")
    pos_file_2 = os.path.join(work_dir, f"{species2}_{species1}.txt")
    
    pos_file = pos_file_1 if os.path.exists(pos_file_1) else (pos_file_2 if os.path.exists(pos_file_2) else None)
    
    if not pos_file or not os.path.exists(lens1) or not os.path.exists(lens2):
        print("Warning: Missing .lens or .txt files for Step 1. Skipping generation (assuming files exist or not needed).")
        return

    outfile = os.path.join(work_dir, f"{species1}_{species2}.corr.txt")

    # 读取 Lens
    def read_lens(fpath):
        lens_map = {}
        pix_map = {}
        start_pix = {}
        cum_len = 0
        first = True
        with open(fpath, 'r') as f:
            for line in f:
                p = line.split()
                if not p: continue
                c, l, sp = p[0], int(p[1]), int(p[2])
                lens_map[c] = l
                if first:
                    start_pix[c] = 200
                    first = False
                else:
                    start_pix[c] = cum_len
                pix_map[c] = sp - start_pix[c]
                cum_len = sp
        return lens_map, pix_map, start_pix

    try:
        l1, p1, s1 = read_lens(lens1)
        l2, p2, s2 = read_lens(lens2)
    except Exception as e:
        print(f"Error reading lens files: {e}")
        return

    with open(pos_file, 'r') as fin, open(outfile, 'w') as fout:
        for line in fin:
            parts = line.strip().split()
            out_parts = []
            for part in parts:
                sub = part.split(':')
                if len(sub) < 5: continue
                rtype, c1, r1, c2, r2 = sub[0], sub[1], sub[2], sub[3], sub[4]
                
                def calc_range(r_str, chrom, lm, pm, sm):
                    clen = lm.get(chrom, 0)
                    plen = pm.get(chrom, 1)
                    spix = sm.get(chrom, 0)
                    rr = r_str.split('-')
                    
                    def parse_val(val, is_end=False):
                        if val == '0': return 0
                        if val == '1' and is_end: return clen
                        if '.' in val: return int(float(val) * clen)
                        if '/' in val: return int(eval(val) * clen)
                        v_seg = int(val) - spix
                        res = int((v_seg / plen) * clen)
                        return res
                    
                    start = parse_val(rr[0])
                    end = parse_val(rr[1], is_end=True)
                    return f"{start}-{end}"

                nr1 = calc_range(r1, c1, l1, p1, s1)
                nr2 = calc_range(r2, c2, l2, p2, s2)
                out_parts.append(f"{rtype}:{c1}:{nr1}:{c2}:{nr2}")
            fout.write("\t".join(out_parts) + "\n")
    print("[Step 1] Done.")

# =========================================================
# STEP 2: 核心匹配 (全兼容版)
# =========================================================
def py_create_cirad_vv(species1, species2, work_dir):
    """
    全兼容匹配算法：
    1. GFF兼容: 支持 Standard GFF3 (col9 ID=...) 和 Custom GFF (col6 ID)
    2. Block兼容: 支持 Standard MCScanX (.collinearity) 和 Custom Block
    3. 方向智能识别
    """
    print(f"[Step 2] Smart Matching for {species1} vs {species2}...")
    
    tc_gff = os.path.join(work_dir, f"{species1}.new.gff")
    sp_gff = os.path.join(work_dir, f"{species2}.new.gff")
    
    base_name = f"{species1}_{species2}"
    rev_name = f"{species2}_{species1}"
    
    corr_file = os.path.join(work_dir, f"{base_name}.corr.txt")
    if not os.path.exists(corr_file): corr_file = os.path.join(work_dir, f"{rev_name}.corr.txt")
    
    # 尝试多种 Block 文件名
    block_file = None
    possible_blocks = [
        f"{base_name}.block.rr.txt", f"{rev_name}.block.rr.txt",
        f"{base_name}.collinearity", f"{rev_name}.collinearity"
    ]
    for pb in possible_blocks:
        if os.path.exists(os.path.join(work_dir, pb)):
            block_file = os.path.join(work_dir, pb)
            break
    
    outfile = os.path.join(work_dir, f"{base_name}.mc.1.txt")

    # --- 1. 加载 GFF (增强版) ---
    gene2pos = {}
    ref_genes = set()
    table = []
    tcgene2order = {}
    tcgenenum = 0

    def load_gff(path, is_ref=False):
        nonlocal tcgenenum
        print(f"  > Loading {os.path.basename(path)}...")
        count = 0
        with open(path, 'r') as f:
            for line in f:
                if line.startswith("#") or not line.strip(): continue
                p = line.strip().split('\t') # GFF3通常是Tab分隔
                if len(p) < 6: p = line.strip().split() # 尝试空格分隔

                gid = None
                pos = 0.0

                # [格式判断逻辑]
                # 情况A: 标准GFF3 (Col 9 has attributes)
                if len(p) >= 9 and ("ID=" in p[8] or "Parent=" in p[8]):
                    # 提取 ID
                    attrs = p[8]
                    # 优先找 ID=，找不到找 Parent=
                    match = re.search(r'ID=([^;]+)', attrs)
                    if not match: match = re.search(r'Parent=([^;]+)', attrs)
                    if match: gid = match.group(1)
                    
                    # 提取位置 (Col 4 Start, Col 5 End -> 取 Start)
                    try: pos = float(p[3])
                    except: pass
                
                # 情况B: 用户定制格式 (Col 6 is ID, Col 7 is Pos)
                elif len(p) > 6:
                    gid = p[5]
                    try: pos = float(p[6])
                    except: pass

                if gid:
                    # 存储双份ID以防后缀不匹配
                    gene2pos[gid] = pos
                    gene2pos[clean_id(gid)] = pos
                    
                    if is_ref:
                        ref_genes.add(clean_id(gid))
                        row = [gid] + [" "] * 6
                        table.append(row)
                        tcgene2order[gid] = tcgenenum
                        tcgene2order[clean_id(gid)] = tcgenenum
                        tcgenenum += 1
                        count += 1
        print(f"    Loaded {count} genes.")

    load_gff(tc_gff, is_ref=True)
    load_gff(sp_gff, is_ref=False)

    # --- 2. 加载 Regions ---
    regions_list = []
    if os.path.exists(corr_file):
        with open(corr_file, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                for p in parts:
                    if p: regions_list.append(p)
    
    # --- 3. 处理 Block (增强版) ---
    type2col = {"A1": 1, "A2": 2, "A3": 3, "A4": 4, "A5": 5, "A6": 6}
    block_lines = []
    match_count = 0
    
    # 智能探测
    ref_col_idx = -1
    qry_col_idx = -1
    is_mcscanx_fmt = False
    
    if not block_file:
        print("Error: No block file found.")
        return

    print(f"  > Processing Blocks ({os.path.basename(block_file)})...")
    
    with open(block_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            # [Block Start Detect]
            # Custom: ">LOCALE" or just starts with ">"
            # MCScanX: "## Alignment"
            
            is_new_block = False
            if line.startswith('>'): 
                is_new_block = True
            elif line.startswith('## Alignment'): 
                is_new_block = True
                is_mcscanx_fmt = True

            if is_new_block:
                if block_lines:
                    # 处理上一个 Block
                    
                    # 自动列检测 (仅一次)
                    if ref_col_idx == -1:
                        # 采样
                        parts = block_lines[0].split()
                        # 如果是 MCScanX 格式: "  1-  0:  GeneA  GeneB  Score"
                        if is_mcscanx_fmt and ':' in parts[1]:
                             # Standard MCScanX: col 2 is Gene1, col 3 is Gene2
                             # 通常 Gene1 是 Ref, Gene2 是 Query，但也可能反过来
                             id_col_2 = clean_id(parts[2])
                             id_col_3 = clean_id(parts[3])
                             
                             if id_col_2 in ref_genes:
                                 ref_col_idx = 2
                                 qry_col_idx = 3
                             else:
                                 ref_col_idx = 3
                                 qry_col_idx = 2
                        else:
                            # Custom Format: ID1 Pos1 ID2 Pos2 or ID1 ID2 ...
                            # 尝试找在 ref_genes 里的列
                            found = False
                            for i, part in enumerate(parts):
                                if clean_id(part) in ref_genes:
                                    ref_col_idx = i
                                    # 假设另一列是 Query。Custom format 通常是 0 和 2
                                    qry_col_idx = 0 if i == 2 else 2
                                    found = True
                                    break
                            if not found:
                                # Default
                                ref_col_idx = 2
                                qry_col_idx = 0
                        print(f"    [Auto-Detect] Ref Column: {ref_col_idx}, Query Column: {qry_col_idx}")

                    # 提取范围
                    try:
                        first_p = block_lines[0].split()
                        last_p = block_lines[-1].split()
                        
                        r_id_s = clean_id(first_p[ref_col_idx])
                        r_id_e = clean_id(last_p[ref_col_idx])
                        q_id_s = clean_id(first_p[qry_col_idx])
                        q_id_e = clean_id(last_p[qry_col_idx])
                        
                        pos_r_s = gene2pos.get(r_id_s, 0)
                        pos_r_e = gene2pos.get(r_id_e, 0)
                        pos_q_s = gene2pos.get(q_id_s, 0)
                        pos_q_e = gene2pos.get(q_id_e, 0)
                        
                        r_min, r_max = min(pos_r_s, pos_r_e), max(pos_r_s, pos_r_e)
                        q_min, q_max = min(pos_q_s, pos_q_e), max(pos_q_s, pos_q_e)

                        # Region 匹配
                        for reg in regions_list:
                            rp = reg.split(':')
                            if len(rp) < 5: continue
                            rtype = rp[0]
                            r1 = rp[2].split('-')
                            min1, max1 = float(r1[0]), float(r1[1])
                            r2 = rp[4].split('-')
                            min2, max2 = float(r2[0]), float(r2[1])
                            
                            # 双向检测
                            match_A_ref = (min1+max1==0) or (r_max >= min1-10 and r_min <= max1+10)
                            match_A_qry = (q_max >= min2-10 and q_min <= max2+10)
                            match_B_qry = (q_max >= min1-10 and q_min <= max1+10)
                            match_B_ref = (min2+max2==0) or (r_max >= min2-10 and r_min <= max2+10)
                            
                            if (match_A_ref and match_A_qry) or (match_B_qry and match_B_ref):
                                col_idx = type2col.get(rtype)
                                if col_idx:
                                    for bl in block_lines:
                                        bp = bl.split()
                                        if len(bp) <= max(ref_col_idx, qry_col_idx): continue
                                        b_ref = bp[ref_col_idx]
                                        b_qry = bp[qry_col_idx]
                                        
                                        r_clean = clean_id(b_ref)
                                        if r_clean in tcgene2order:
                                            row_idx = tcgene2order[r_clean]
                                            table[row_idx][col_idx] = b_qry
                                            match_count += 1
                                    break
                    except Exception as e:
                        # Skip malformed blocks
                        pass

                block_lines = []
                continue
            
            # 收集 Block 内容行
            # 忽略表头注释行
            if line.startswith('#') or line.startswith('the') or line.startswith('Score'):
                continue
            
            block_lines.append(line)

    print(f"  > Total Matches Filled: {match_count}")
    
    with open(outfile, 'w') as f:
        for row in table:
            data = row[1:]
            depth = sum(1 for x in data if x.strip())
            f.write(",".join(row) + f",{depth}\n")
    print("[Step 2] Done.")

# =========================================================
# STEP 3-5: 格式化工具
# =========================================================
def py_split_to_tab(species1, species2, work_dir):
    infile = os.path.join(work_dir, f"{species1}_{species2}.mc.1.txt")
    outfile = os.path.join(work_dir, f"{species1}_{species2}.mc.2.txt")
    if not os.path.exists(infile): return
    with open(infile, 'r') as fin, open(outfile, 'w') as fout:
        for line in fin:
            parts = line.strip().split(',')
            fout.write("\t".join(parts[:5]) + "\n")

def py_fill_in_dot(species1, species2, work_dir):
    infile = os.path.join(work_dir, f"{species1}_{species2}.mc.2.txt")
    outfile = os.path.join(work_dir, f"{species1}_{species2}.mc.3.txt")
    if not os.path.exists(infile): return
    with open(infile, 'r') as fin, open(outfile, 'w') as fout:
        for line in fin:
            parts = line.strip().split('\t')
            new_p = [p if any(c.isalnum() for c in p) else "." for p in parts]
            while len(new_p) < 4: new_p.append(".")
            fout.write("\t".join(new_p[:4]) + "\n")

def py_create_mc(species1, species2, work_dir):
    mc_file = os.path.join(work_dir, f"{species1}_{species2}.mc.1.txt")
    blast_file = os.path.join(work_dir, f"{species1}_{species2}.blast")
    out_file = os.path.join(work_dir, f"{species1}_{species2}.new.blast")
    
    if not os.path.exists(mc_file) or not os.path.exists(blast_file): return
    
    valid_pairs = set()
    with open(mc_file, 'r') as f:
        for line in f:
            parts = line.strip().replace(',', '\t').split('\t')
            if not parts: continue
            ref_gene = clean_id(parts[0])
            for q_gene in parts[1:]:
                if 'g' in q_gene or 'Gene' in q_gene or 'v' in q_gene: # 宽松匹配
                    valid_pairs.add(f"{ref_gene}|{clean_id(q_gene)}")
    
    with open(blast_file, 'r') as fin, open(out_file, 'w') as fout:
        for line in fin:
            p = line.split()
            if len(p) < 2: continue
            q, r = clean_id(p[0]), clean_id(p[1])
            if f"{r}|{q}" in valid_pairs or f"{q}|{r}" in valid_pairs:
                fout.write(line)

# =========================================================
# STEP 6: 绘图 (全兼容版)
# =========================================================
def py_draw_dotplot(species1, species2, work_dir):
    print(f"[Step 6] Drawing Dotplot...")
    blast_file = os.path.join(work_dir, f"{species1}_{species2}.new.blast")
    if not os.path.exists(blast_file):
        print("Error: new.blast file missing.")
        return

    # 加载坐标 (保持原逻辑不变)
    def load_loc(spec):
        lens_f = os.path.join(work_dir, f"{spec}.lens")
        gff_f = os.path.join(work_dir, f"{spec}.new.gff")
        
        chr_len = {}
        chr_start = {}
        curr = 0
        with open(lens_f, 'r') as f:
            for line in f:
                p = line.split()
                if p:
                    c, l = p[0], float(p[1])
                    clean_c = re.sub(r'^\D+', '', c).lstrip('0')
                    chr_len[clean_c] = l
                    chr_start[clean_c] = curr
                    curr += l
        
        total = curr
        step = (5/6) / total if total > 0 else 0
        loc_map = {}
        
        with open(gff_f, 'r') as f:
            for line in f:
                if line.startswith("#"): continue
                p = line.strip().split('\t')
                if len(p) < 6: p = line.strip().split()
                
                gid = None
                pos = 0.0
                if len(p) >= 9 and "ID=" in p[8]:
                    m = re.search(r'ID=([^;]+)', p[8])
                    if m: gid = m.group(1)
                    try: pos = float(p[3])
                    except: pass
                elif len(p) > 6:
                    gid = p[5]
                    try: pos = float(p[6])
                    except: pass
                    
                if gid:
                    c_raw = p[0]
                    c_clean = re.sub(r'^\D+', '', c_raw).lstrip('0')
                    if c_clean in chr_start:
                        abs_pos = (chr_start[c_clean] + pos) * step
                        loc_map[clean_id(gid)] = abs_pos
        return loc_map, chr_len, step

    try:
        loc1, cl1, st1 = load_loc(species1)
        loc2, cl2, st2 = load_loc(species2)
    except Exception as e:
        print(f"Error loading locations: {e}")
        return
    
    x, y, cols = [], [], []
    c_list = ['red', 'blue', 'gray']
    seen = {} 
    
    with open(blast_file, 'r') as f:
        for line in f:
            p = line.split()
            id_a, id_b = clean_id(p[0]), clean_id(p[1])
            
            pos_x, pos_y = None, None
            q_id = None
            
            if id_a in loc2 and id_b in loc1:
                pos_x, pos_y = loc2[id_a], loc1[id_b]
                q_id = id_a
            elif id_b in loc2 and id_a in loc1:
                pos_x, pos_y = loc2[id_b], loc1[id_a]
                q_id = id_b
            else: continue
            
            rank = seen.get(q_id, 0)
            if rank >= 20: continue 
            col = c_list[0] if rank == 0 else (c_list[1] if rank < 5 else c_list[2])
            seen[q_id] = rank + 1
            
            y.append(11/12 - pos_y)
            x.append(1/12 + pos_x)
            cols.append(col)
            
    # --- 关键修改：使用面向对象绘图 (Object-Oriented Plotting) ---
    fig, ax = plt.subplots(figsize=(8, 8), dpi=300) # 创建独立的 fig 和 ax
    
    ax.scatter(x, y, s=0.5, c=cols, marker='.', edgecolors='none')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    # Grid & Labels
    cy = 11/12
    for c, l in cl1.items():
        sl = l * st1
        cy -= sl
        # 替换 plt.axhline 为 ax.axhline
        ax.axhline(cy, xmin=1/12, xmax=11/12, color='k', linewidth=0.1)
        # 替换 plt.text 为 ax.text
        ax.text(1/12 - 0.01, cy + sl/2, c, fontsize=6, ha='right')
        
    cx = 1/12
    for c, l in cl2.items():
        sl = l * st2
        cx += sl
        ax.axvline(cx, ymin=1/12, ymax=11/12, color='k', linewidth=0.1)
        ax.text(cx - sl/2, 11/12 + 0.01, c, fontsize=6, ha='center')

    ax.text(0.02, 0.5, species1, rotation=90, fontsize=14, ha='center')
    ax.text(0.5, 0.98, species2, fontsize=14, ha='center')
    
    out_png = os.path.join(work_dir, f"{species1}_{species2}_corr.png")
    
    # 保存并显式关闭当前特定的 figure
    fig.savefig(out_png)
    plt.close(fig) 
    
    print(f"[Step 6] Plot saved: {out_png}")

# =========================================================
# 主控流程
# =========================================================
def zu_correspondence_mc_run_tools(full_work_dir, shu_name, heng_name):
    # 移除原本的 os.path.join(FILE_KEEP_DIR, place)
    work_dir = full_work_dir 
    
    print(f"🚀 开始分析 (全兼容 v3.0) | Ref: {shu_name} vs Query: {heng_name}")
    print(f"📂 工作目录: {work_dir}") # 增加日志方便调试
    
    if not os.path.exists(work_dir):
        raise FileNotFoundError(f"Work directory not found: {work_dir}")

    try:
        py_tran_position(shu_name, heng_name, work_dir)
        py_create_cirad_vv(shu_name, heng_name, work_dir)
        py_split_to_tab(shu_name, heng_name, work_dir)
        py_fill_in_dot(shu_name, heng_name, work_dir)
        py_create_mc(shu_name, heng_name, work_dir)
        py_draw_dotplot(shu_name, heng_name, work_dir)
        print("✅ 分析成功完成")
    except Exception as e:
        print("❌ 分析出错")
        traceback.print_exc()
        raise e