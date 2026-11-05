#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

# 设置后端，防止在无显示器的服务器上报错
plt.switch_backend('Agg')

class DotplotBlock:
    def __init__(self, num_process, suffix, block_num, bed_path, block_blast_path, result_path, name_change):
        self.num_process = num_process
        self.suffix = suffix
        self.name_change = name_change
        self.block_num = block_num
        self.bed = os.path.join('.', bed_path)
        self.block_blast_path = os.path.join('.', block_blast_path)
        self.result_path = os.path.join('.', result_path)

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def clean_id(self, gene_id):
        """标准化 ID：去除空格和 .1 等版本后缀"""
        if not isinstance(gene_id, str):
            gene_id = str(gene_id)
        gene_id = gene_id.strip()
        # 如果物种名本身包含点（如 Species.1），请注释掉下面两行
        if '.' in gene_id:
            gene_id = gene_id.split('.')[0]
        return gene_id

    def get_block(self, path):
        """读取 Block 文件并建立 ID 映射字典"""
        filename = os.path.basename(path)
        print(f"--- [DEBUG] Reading Block File: {filename} ---")
        
        gene_dit = {}
        block = []
        total_blocks_found = 0
        blocks_skipped_size = 0
        
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for li in f:
                    li = li.strip()
                    if not li: continue
                    is_header = False
                    if 'MAXIMUM' in li or '++++' in li: continue
                    if 'path length' in li or 'Alignment' in li: is_header = True
                    
                    if is_header:
                        added = self.process_block_buffer(block, gene_dit)
                        if len(block) > 0:
                            total_blocks_found += 1
                            if not added: blocks_skipped_size += 1
                        block = [] 
                    else:
                        block.append(li)
            
            # 处理最后一个 Block
            added = self.process_block_buffer(block, gene_dit)
            if len(block) > 0:
                total_blocks_found += 1
                if not added: blocks_skipped_size += 1

        except Exception as e:
            print(f"Error reading block file {path}: {e}")
        
        print(f"    Total Blocks Detected: {total_blocks_found}")
        print(f"    Total Gene Pairs Loaded: {len(gene_dit)}")
        return gene_dit

    def process_block_buffer(self, block, gene_dit):
        if not block: return False
        if len(block) < self.block_num: return False

        valid = 0
        for row in block:
            rows = row.strip().split()
            if len(rows) < 2: continue
            g1, g2 = None, None
            
            # 兼容多种 Block 格式
            if len(rows) >= 3 and self.is_number(rows[1]): # User Special
                g1, g2 = rows[0], rows[2]
            elif len(rows) >= 4 and '-' in rows[0] and ':' in rows[1]: # MCScanX
                g1, g2 = rows[2], rows[3]
            elif len(rows) >= 2 and not self.is_number(rows[1]): # Simple
                g1, g2 = rows[0], rows[1]

            if g1 and g2:
                g1 = self.clean_id(g1.rstrip(':'))
                g2 = self.clean_id(g2.rstrip(':'))
                gene_dit[g1] = g2
                valid += 1
        return valid > 0

    def gene_location(self, gff, lens, step, spec_name):
        """读取 GFF 获取基因坐标"""
        print(f"--- [DEBUG] Processing GFF for {spec_name} ---")
        loc_gene, dict_chr, n = {}, {}, 0
        
        # 建立染色体偏移量
        for i in lens.index:
            dict_chr[str(i)] = n
            n += float(lens.at[i, 1])
        
        # 探测 GFF 列
        gff_mode = 'standard'
        if not gff.empty and gff.shape[1] >= 7 and self.is_number(gff.iloc[0, 6]): 
            gff_mode = 'user_special'

        mapped_count = 0
        for k in gff.index:
            raw_chr = str(gff.loc[k, 0])
            real_chr = None
            # 模糊匹配染色体 ID
            if raw_chr in dict_chr: real_chr = raw_chr
            else:
                c1 = f"{spec_name}{raw_chr.zfill(2)}"
                c2 = f"{spec_name}{raw_chr}"
                if c1 in dict_chr: real_chr = c1
                elif c2 in dict_chr: real_chr = c2
            
            if not real_chr: continue 

            try:
                if gff_mode == 'user_special':
                    gene_id_raw = str(gff.loc[k, 5])
                    pos_val = float(gff.loc[k, 6])
                else:
                    gene_id_raw = str(gff.loc[k, 1])
                    pos_val = float(gff.loc[k, 2])
                
                gene_id = self.clean_id(gene_id_raw)
                loc = (float(dict_chr[real_chr]) + pos_val) * step
                loc_gene[gene_id] = loc
                mapped_count += 1
                if mapped_count == 1:
                     print(f"    [Sample] GFF ID: '{gene_id}' (Raw: '{gene_id_raw}')")
            except: continue
        
        print(f"    Mapped {mapped_count} genes.")
        return loc_gene

    def select_blast(self, blast_path, block_path):
        """读取并过滤 Blast，返回 DataFrame"""
        print(f"--- [DEBUG] Filtering BLAST ---")
        gene_pair_list, pair_pos, last_na1, last_na2, result_pair, num = [], {}, '', '', [], 1
        
        gene_dit = self.get_block(block_path)
        if not gene_dit: return pd.DataFrame()

        try:
            line_count = 0
            with open(blast_path, 'r') as f:
                for li in f:
                    line_count += 1
                    lis = li.strip().split()
                    if len(lis) < 2: continue 
                    if 'Scaffold' in li or lis[0] == lis[1]: continue
                    
                    q = self.clean_id(lis[0])
                    s = self.clean_id(lis[1])
                    
                    hit = False
                    if q in gene_dit and gene_dit[q] == s: hit = True
                    elif s in gene_dit and gene_dit[s] == q: hit = True
                    
                    if hit:
                        gene_pair_list.append(f'{q}\t{s}')
                    
                    if last_na1 == q and last_na2 != s: num += 1
                    else: num = 1
                    pair_pos[f'{q}\t{s}'] = str(num)
                    last_na1, last_na2 = q, s
            print(f"    Scanned {line_count} lines. Found {len(gene_pair_list)} pairs.")
        except Exception as e:
            print(f"Error reading blast: {e}")
            return pd.DataFrame()

        for pair in gene_pair_list:
            if pair in pair_pos:
                row = pair.split('\t')
                row.append(pair_pos[pair])
                result_pair.append(row)

        return pd.DataFrame(result_pair)

    def plot_chr1(self, lens, gl, gl2, step, mark, name): 
        # 绘制 Y 轴物种 (Species 1)
        gl_start, n, start_x = 11/12, 0, 1/12
        mark_y = 17/240
        align1 = dict(family='sans-serif', style='italic', horizontalalignment="center", verticalalignment="center")
        for k in lens.index:
            n += float(lens.at[k, 1])
            x = gl_start - float(n) * step
            plt.plot([start_x, start_x + gl2], [x, x], linestyle='-', color='black', linewidth=0.125)
        plt.plot([start_x, start_x + gl2], [gl_start, gl_start], linestyle='-', color='black', linewidth=0.375, alpha=0.5)
        plt.text(mark_y-0.04, 0.5 * (2 * gl_start - gl), name, color='black', fontsize=20, rotation=90, weight='semibold', **align1)

    def plot_chr2(self, lens, gl, gl2, step, mark, name):
        # 绘制 X 轴物种 (Species 2)
        gl_start, n, start_x = 1/12, 0, 11/12
        mark_y = 223/240
        align1 = dict(family='sans-serif', style='italic', horizontalalignment="center", verticalalignment="center")
        for k in lens.index:
            n += float(lens.at[k, 1])
            x = gl_start + float(n) * step
            plt.plot([x, x], [start_x, start_x - gl2], linestyle='-', color='black', linewidth=0.125)
        plt.plot([gl_start, gl_start], [start_x, start_x - gl2], linestyle='-', color='black', linewidth=0.375, alpha=0.5)
        plt.text(0.5 * (2 * gl_start + gl)+0.07, mark_y + 0.03, name, color='black', fontsize=20, rotation=0, weight='semibold', **align1)

    def pair_positon(self, data, loc1, loc2, colors, s1_col=0, s2_col=1):
        """
        核心修复：增加 s1_col 和 s2_col 参数
        允许指定 Blast 的哪一列对应 Species 1 (Y轴)，哪一列对应 Species 2 (X轴)
        """
        pos1, pos2, newcolor = [], [], []
        gl_start1, gl_start2 = 11 / 12, 1 / 12
        
        for index, k in data.iterrows():
            id_s1 = k[s1_col] # 应该在 Species 1 GFF 里的 ID
            id_s2 = k[s2_col] # 应该在 Species 2 GFF 里的 ID
            
            if id_s1 not in loc1 or id_s2 not in loc2:
                continue
                
            # 计算坐标
            # Spec 1 画在 Y 轴 -> 使用 gl_start1 减去偏移
            x_coord_on_plot = gl_start1 - loc1[id_s1] 
            # Spec 2 画在 X 轴 -> 使用 gl_start2 加上偏移
            y_coord_on_plot = gl_start2 + loc2[id_s2]
            
            # 注意：plt.scatter(x, y) 里的 x 是水平轴，y 是垂直轴
            # 我们的 plot_chr2 (Spec2) 是水平的，所以 scatter 的 x 应该是 Spec 2 的坐标
            # 我们的 plot_chr1 (Spec1) 是垂直的，所以 scatter 的 y 应该是 Spec 1 的坐标
            
            pos1.append(y_coord_on_plot) # Scatter X (Spec 2 location)
            pos2.append(x_coord_on_plot) # Scatter Y (Spec 1 location)
            
            color = colors[0] if k[2] == '1' else colors[1]
            newcolor.append(color)
            
        return pos1, pos2, newcolor

    def plotfig(self, spec1, spec2):
        print(f"Processing Dotplot: {spec1} (Y-Axis) vs {spec2} (X-Axis) ...")
        plt.figure(figsize=(8, 8), dpi=300)
        root = plt.axes([0, 0, 1, 1])
        
        try:
            gff_1 = pd.read_csv(f'{self.bed}/{spec1}.new.gff', sep="\t", header=None, comment='#', error_bad_lines=False, dtype=str)
            gff_2 = pd.read_csv(f'{self.bed}/{spec2}.new.gff', sep="\t", header=None, comment='#', error_bad_lines=False, dtype=str)
            lens_1 = pd.read_csv(f'{self.bed}/{spec1}.lens', sep="\t", header=None, index_col=0)
            lens_2 = pd.read_csv(f'{self.bed}/{spec2}.lens', sep="\t", header=None, index_col=0)
        except Exception as e:
            print(f"Error loading files: {e}")
            return

        gl1, gl2 = 5/6, 5/6
        step1 = gl1 / float(lens_1[1].sum())
        step2 = gl2 / float(lens_2[1].sum())
        
        self.plot_chr1(lens_1, gl1, gl2, step1, '', self.name_change[spec1])
        self.plot_chr2(lens_2, gl1, gl2, step2, '', self.name_change[spec2])
        
        gene_loc_1 = self.gene_location(gff_1, lens_1, step1, spec1)
        gene_loc_2 = self.gene_location(gff_2, lens_2, step2, spec2)
        
        blast = self.select_blast(f'{self.block_blast_path}/{spec1}_{spec2}.{self.suffix}',
                                  f'{self.block_blast_path}/{spec1}_{spec2}.block.rr.txt')
        
        print(f"--- [DEBUG] Auto-Detecting Species Columns ---")
        if not blast.empty:
            # 智能检测：哪一列是 Species 1？
            # 统计 blast 第一列有多少 ID 能在 Species 1 GFF 中找到
            col0_is_s1 = blast[0].isin(gene_loc_1.keys()).sum()
            col0_is_s2 = blast[0].isin(gene_loc_2.keys()).sum()
            
            print(f"    Blast Col 0 matches Spec 1 ({spec1}): {col0_is_s1} times")
            print(f"    Blast Col 0 matches Spec 2 ({spec2}): {col0_is_s2} times")
            
            s1_col, s2_col = 0, 1
            if col0_is_s2 > col0_is_s1:
                print("    [ALERT] Detected SWAPPED Species Order! Adapting...")
                s1_col = 1 # Spec 1 (Y-axis) is actually in Blast Col 1
                s2_col = 0 # Spec 2 (X-axis) is actually in Blast Col 0
            else:
                print("    [INFO] Species Order is Standard.")

            colors = ['orangered', 'gray']
            # 将正确的列索引传给绘图函数
            x, y, colors = self.pair_positon(blast, gene_loc_1, gene_loc_2, colors, s1_col=s1_col, s2_col=s2_col)
            
            if len(x) == 0:
                print("    [DEBUG] Plot is empty! Check GFF IDs vs Blast IDs carefully.")
            else:
                print(f"    [SUCCESS] Plotting {len(x)} points.")
                
            plt.scatter(x, y, s=1, c=colors, alpha=0.5, edgecolors='none', linewidths=0)
        else:
            print(f"    [DEBUG] Warning: Blast dataframe empty.")

        root.set_xlim(0, 1)
        root.set_ylim(0, 1)
        root.set_axis_off()
        output = f'{self.result_path}/{spec1}_{spec2}.{self.block_num}.2400.png'
        plt.savefig(output)
        print(f"Saved: {output}")
        plt.close()

    def main(self):
        blasts = glob.glob(f'{self.block_blast_path}/*.blast')
        for file in blasts:
            fna = os.path.basename(file)
            spec1, spec2 = fna.split('.')[0].split('_')
            self.plotfig(spec1, spec2)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python dotplot_block.2400.pd.py <Species1> <Species2> <BlockNum>")
        sys.exit(1)
        
    num_process = 1
    blast_suffix = 'blast'
    block_num = int(sys.argv[3])
    bed_path = ''
    block_blast_path = ''
    result_path = ''
    name_change = {f"{sys.argv[1]}": f"{sys.argv[1]}", f"{sys.argv[2]}": f"{sys.argv[2]}"}
    
    p = DotplotBlock(num_process, blast_suffix, block_num, bed_path, block_blast_path, result_path, name_change)
    p.main()