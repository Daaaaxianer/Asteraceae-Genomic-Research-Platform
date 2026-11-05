#!/usr/bin/env python
# -*- coding:utf-8 -*-

import re
import os
import sys

# === 纯净版 gene_calc.py ===
# 修复说明：已移除 logging 配置，防止 "unable to load configuration" 报错

class GeneProcessor:
    def __init__(self, input_file_path, output_file_path):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path

    def get_chromosome(self, gene_id):
        """
        从基因ID中提取染色体编号
        """
        try:
            # 匹配 At1g... 这种格式 (非数字开头 + 数字 + g/G)
            match = re.search(r'\D+(\d+)[gG]', gene_id)
            if match:
                return match.group(1)
            
            # 匹配开头就是数字的情况
            match_start = re.match(r'(\d+)', gene_id)
            if match_start:
                return match_start.group(1)
                
            # 兜底匹配任意数字
            match_any = re.search(r'(\d+)', gene_id)
            if match_any:
                return match_any.group(1)
                
            return "Unk"
        except Exception:
            return "Unk"

    def process_input_file(self):
        mc = []
        array = []
        retain = []

        print(f"Reading file: {self.input_file_path}")
        
        try:
            with open(self.input_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行、注释行、Block头行
                    if not line or line.startswith("#") or line.startswith("Block"):
                        continue
                    
                    # 兼容 tab 和 空格分割
                    arr = line.split() if '\t' not in line else line.split('\t')
                    
                    if len(arr) < 2:
                        continue

                    # 判断最后一列是否是 Block ID (纯数字)
                    last_col = arr[-1].strip()
                    is_block_id = False
                    
                    if last_col.isdigit():
                        is_block_id = True
                    
                    if is_block_id:
                        # 格式: [Ref, Gene1, Gene2, ..., BlockID] -> 去掉 BlockID
                        matched_genes = arr[1:-1]
                    else:
                        # 格式: [Ref, Gene1, Gene2, ...]
                        matched_genes = arr[1:]

                    # 提取染色体 (基于第一列 Reference Gene ID)
                    ch = self.get_chromosome(arr[0])
                    array.append([ch] + matched_genes)

        except Exception as e:
            print(f"Error reading file: {e}")
            raise e

        print(f"Total lines processed: {len(array)}")

        # === 计算保留率逻辑 (滑动窗口) ===
        total_len = len(array)
        for i in range(total_len):
            chr_name = array[i][0]
            current_row_result = [chr_name]
            
            # 确定窗口范围 (前后50行)，防止索引越界
            start_index = max(0, i - 50)
            end_index = min(total_len, i + 51) 

            # array[i] 结构: [Chr, Gene1, Gene2...]
            # 第一列是Chr，所以从索引1开始遍历物种列
            num_columns = len(array[i])
            
            for j in range(1, num_columns):
                total_genes_in_window = 0
                retained_genes_count = 0
                
                # 在窗口内遍历
                for k in range(start_index, end_index):
                    # 必须是同一条染色体才计入统计
                    if array[k][0] != chr_name:
                        continue
                    
                    total_genes_in_window += 1
                    
                    # 检查对应列的基因是否存在
                    if j < len(array[k]):
                        gene_val = array[k][j]
                        # '.' 和 '-' 通常表示缺失
                        if gene_val and gene_val not in ('.', '-'):
                            retained_genes_count += 1
                
                ave_retain = 0
                if total_genes_in_window > 0:
                    ave_retain = retained_genes_count / total_genes_in_window
                
                current_row_result.append(f"{ave_retain:.4f}")
            
            retain.append(current_row_result)
            
        return retain

    def write_output_file(self, data):
        if not data:
            return

        # 动态生成表头: chr, retain1, retain2...
        col_count = len(data[0]) - 1
        header = "chr" + "\t" + "\t".join([f"retain{i+1}" for i in range(col_count)])
        
        # 确保 output 目录存在
        if not os.path.exists("output"):
            os.makedirs("output")

        output_full_path = os.path.join("output", self.output_file_path)
        
        print(f"Writing result to: {output_full_path}")
        with open(output_full_path, "w", encoding='utf-8') as out:
            out.write(header + "\n")
            for row in data:
                out.write("\t".join(map(str, row)) + "\n")

if __name__ == '__main__':
    # 脚本入口
    print("Script started...")
    
    # 检查输入目录是否存在
    if not os.path.exists("orthomcl"):
        print("Error: 'orthomcl' directory not found.")
        # 在服务器环境不需要 exit(1) 强制退出，打印错误即可，防止 web 进程崩溃
    else:
        input_files = [f for f in os.listdir("orthomcl") if os.path.isfile(os.path.join("orthomcl", f))]
        print(f"Found input files: {input_files}")
        
        if not input_files:
            print("Error: No files found in orthomcl/ folder.")
        
        for filename in input_files:
            try:
                input_path = os.path.join("orthomcl", filename)
                # 生成输出文件名: raw.txt -> raw_retain.txt
                file_name_no_ext = filename.rsplit(".", 1)[0]
                output_file_name = f"{file_name_no_ext}_retain.txt"

                print(f"Processing {input_path}...")
                gene_processor = GeneProcessor(input_path, output_file_name)
                processed_data = gene_processor.process_input_file()
                gene_processor.write_output_file(processed_data)
                print(f"Done: {output_file_name}")
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                import traceback
                traceback.print_exc()