#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :tools.py

import os
import sys
import glob
import shutil
import traceback
import subprocess
from concurrent.futures import ThreadPoolExecutor

# =========================================================
# 1. 绘图库防崩溃设置
# =========================================================
import matplotlib
# 强制使用非交互式后端，防止 Windows 桌面应用崩溃或弹窗冻结
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

from Bio import SeqIO, Phylo

# =========================================================
# 2. 路径与环境配置
# =========================================================

def get_real_base_dir():
    """
    获取项目根目录 (用于定位 file_keep)
    结构: .../tools/offline_views/Draw_list_trees/tools.py
    修正：向上回溯 4 层以找到项目根目录
    """
    current_file_path = os.path.abspath(__file__)
    # 回溯顺序: Draw_list_trees -> offline_views -> tools -> Asteraceae (Root)
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))))
    return root_dir

path_get = get_real_base_dir()

def get_tool_path(tool_name):
    """
    获取外部工具路径 (bin 文件夹)
    修正：bin 文件夹就在当前 tools.py 同级目录下，不需要去根目录找
    """
    # 获取 tools.py 所在的文件夹 (.../Draw_list_trees)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 在当前目录下找 bin
    bin_dir = os.path.join(current_dir, 'bin')
    
    if os.name == 'nt': # Windows
        exe_path = os.path.join(bin_dir, f"{tool_name}.exe")
        if os.path.exists(exe_path):
            return exe_path 
            
    local_tool = os.path.join(bin_dir, tool_name)
    if os.path.exists(local_tool):
        return local_tool
        
    return tool_name # 环境变量兜底

# =========================================================
# 3. 核心业务逻辑类
# =========================================================

class ListTree:
    def __init__(self, work_dir, vvi_file, additional_parameter=False):
        """
        :param work_dir: 当前任务的绝对路径工作目录
        :param vvi_file: list 文件名
        """
        self.work_dir = work_dir
        # 获取工作目录下所有的 pep/fasta 文件的绝对路径
        self.input_pep_files = glob.glob(os.path.join(work_dir, "*.pep")) + \
                               glob.glob(os.path.join(work_dir, "*.fasta"))
        
        self.vvi_file = os.path.join(work_dir, vvi_file)
        self.output_dir = os.path.join(work_dir, "output")
        self.additional_parameter = str(additional_parameter).lower() == 'true'

    def pep_files_ids(self):
        """读取所有 PEP 文件并建立索引"""
        pep_gene_ids = {}
        for file_path in self.input_pep_files:
            # 获取文件名作为 key
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                # 解析 Fasta
                records = {record.id: str(record.seq).replace("*", "").replace(".", "") 
                           for record in SeqIO.parse(file_path, "fasta")}
                pep_gene_ids[file_name] = records
            except Exception as e:
                print(f"Warning: Failed to parse {file_path}: {e}")
        return pep_gene_ids

    def write_tree_file(self, sp_geneid_dict):
        """根据 list.txt 提取序列写入 output 文件夹"""
        # 使用绝对路径清理/创建 output 目录
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        if not os.path.exists(self.vvi_file):
            print(f"Error: {self.vvi_file} not found.")
            return

        with open(self.vvi_file, 'r', encoding='utf-8') as mc_file:
            for line in mc_file:
                parts = line.strip().split()
                if not parts: continue
                
                vvi_name = parts[0]
                # 目标文件使用绝对路径
                target_file = os.path.join(self.output_dir, f'{vvi_name}.txt')
                
                with open(target_file, 'w', encoding='utf-8') as new_file:
                    for gene_name in parts:
                        if gene_name == "." or gene_name == vvi_name:
                            continue
                        
                        # 解析物种名逻辑: 假设基因名为 Speciesg001 -> 取 Species
                        try:
                            species_key = ''.join(filter(str.isalpha, gene_name.split("g")[0]))
                            
                            # 注意：这里要求 pep 文件名必须和 species_key 一致
                            if species_key in sp_geneid_dict and gene_name in sp_geneid_dict[species_key]:
                                seq = sp_geneid_dict[species_key][gene_name]
                                new_file.write(f">{gene_name}\n{seq}\n")
                        except Exception:
                            continue

    def draw_tree(self, tree_file_path):
        """绘图逻辑"""
        try:
            # tree_file_path 已经是绝对路径
            tree = Phylo.read(tree_file_path, "newick")
            
            # 尝试定根
            if self.additional_parameter:
                base_name = os.path.basename(tree_file_path).split("_BS_50")[0]
                outgroup = next((node for node in tree.find_clades() if node.name == base_name), None)
                if outgroup:
                    tree.root_with_outgroup(outgroup)
            
            # 保存定根后的 Newick 文件
            rooted_name = tree_file_path.replace(".tree", "_root_file.newick")
            Phylo.write(tree, rooted_name, 'newick')
            
            # 绘制 PNG 图片
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(1, 1, 1)
            Phylo.draw(tree, axes=ax, do_show=False)
            
            png_name = tree_file_path.replace(".tree", "_root_png.png")
            plt.savefig(png_name)
            plt.close(fig) # 显式关闭，释放内存
            
        except Exception as e:
            print(f"Draw Error [{tree_file_path}]: {e}")

    def run_single_task(self, txt_file):
        """单个同源组的处理流水线: Muscle -> FastTree -> Draw"""
        try:
            # txt_file 是绝对路径
            base_path = os.path.splitext(txt_file)[0]
            
            muscle = get_tool_path('muscle')
            fasttree = get_tool_path('FastTree')
            
            clw_file = f"{base_path}.clw"
            tree_file = f"{base_path}.tree"
            
            # 1. Muscle 比对 (列表传参，安全处理空格路径)
            # 相当于: muscle -in input.txt -out output.clw
            cmd_muscle = [muscle, "-in", txt_file, "-out", clw_file]
            subprocess.run(cmd_muscle, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(clw_file):
                print(f"Muscle failed for {txt_file}")
                return

            # 2. FastTree 建树 (FastTree 输出到 stdout，需要捕获)
            # 相当于: FastTree input.clw > output.tree
            cmd_tree = [fasttree, clw_file]
            with open(tree_file, "w") as outfile:
                subprocess.run(cmd_tree, stdout=outfile, check=True)
            
            # 3. 处理结果
            if os.path.exists(tree_file) and os.path.getsize(tree_file) > 0:
                final_tree = f"{base_path}_BS_50.tree"
                shutil.copy(tree_file, final_tree)
                self.draw_tree(final_tree)
                
        except subprocess.CalledProcessError as e:
            # subprocess 报错会进入这里
            print(f"Tool execution failed for {txt_file}: {e}")
        except Exception as e:
            print(f"Task Failed {txt_file}: {e}")
            traceback.print_exc()

    def run(self):
        sp_geneid_dict = self.pep_files_ids()
        self.write_tree_file(sp_geneid_dict)
        
        # 查找绝对路径下的 txt 文件
        txt_files = glob.glob(os.path.join(self.output_dir, "*.txt"))
        
        if not txt_files:
            print(f"No output files generated in {self.output_dir}")
            return

        # 并发执行
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(self.run_single_task, txt_files)

# =========================================================
# 4. 对外接口
# =========================================================

def draw_list_tree_run_tools(place, patten):
    """
    视图函数调用的入口
    place: file_keep 下的文件夹 UUID
    """
    # 1. 构造绝对路径的工作目录
    work_dir = os.path.join(path_get, 'file_keep', place)
    
    try:
        if not os.path.exists(work_dir):
            print(f"Error: Work directory {work_dir} does not exist.")
            return

        # 2. 不再使用 os.chdir()，而是将路径传入类中
        # 此时 list.txt 就在 work_dir 下
        tree_runner = ListTree(work_dir, "list.txt", additional_parameter=patten)
        tree_runner.run()
        
        # ------------------------------------------------------------------
        # 清理逻辑：将 output 文件夹内的结果移到 work_dir 根目录
        # ------------------------------------------------------------------
        output_dir = tree_runner.output_dir
        
        if os.path.exists(output_dir):
            # 1. 移动所有文件到 work_dir
            for res_file in glob.glob(os.path.join(output_dir, "*")):
                try:
                    # shutil.move(src, dst) - 移动到 work_dir
                    shutil.move(res_file, work_dir)
                except Exception as e:
                    print(f"Move error: {e}")
            
            # 2. 删除空的 output 文件夹
            try:
                shutil.rmtree(output_dir)
            except Exception:
                pass 

    except Exception as e:
        traceback.print_exc()