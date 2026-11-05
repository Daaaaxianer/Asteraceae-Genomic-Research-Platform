#!/usr/bin/env python
# -*- coding:utf-8 -*-

import re
import os
import sys
import traceback
import datetime

class GeneAnalysis_diushi:
    def __init__(self, input_file, output_file, logger):
        self.input_file = input_file
        self.output_file = output_file
        self.logger = logger
        self.array = []
        self.n = 0
        self.all = []
        self.hash = {}

    def log(self, msg):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.logger.write(f"[{timestamp}] {msg}\n")
        print(msg)

    def read_input(self):
        self.log(f"正在读取文件: {self.input_file}")
        valid_lines = 0
        try:
            with open(self.input_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line: continue 
                    
                    # 调试：打印前几行
                    if line_num <= 3:
                        self.log(f"Line {line_num} preview: {line[:50]}...")

                    if 'scaffold' in line: continue
                    # 排除特定格式 (根据原逻辑)
                    if re.search(r'\d+s\d+', line): continue
                    
                    # 【修复1】使用 split() 不带参数，自动处理 空格 和 Tab
                    arr = line.split()

                    if len(arr) < 2:
                        continue

                    # 更新最大列数
                    curr_cols = len(arr) - 1
                    if curr_cols > self.n:
                        self.n = curr_cols
                    
                    # 核心筛选：首列必须包含数字作为染色体标识
                    match = re.search(r'\d+', arr[0])
                    if match:
                        chr_num = match.group()
                        arr[0] = chr_num
                        self.array.append(arr)
                        valid_lines += 1
                    else:
                        if line_num <= 10: 
                            self.log(f"Line {line_num}: Skipped (No chr number)")
                        
            self.log(f"读取完成。有效行数: {valid_lines}, 最大列数: {self.n + 1}")
            
        except Exception as e:
            self.log(f"读取文件出错: {str(e)}")
            traceback.print_exc()
            raise e # 抛出异常以便主程序捕获

    def process_data(self):
        if not self.array:
            self.log("警告: 数组为空，没有数据可处理。")
            return

        self.log(f"开始分析数据... (Rows: {len(self.array)}, Data Cols: {self.n})")
        
        try:
            # 【修复2】重写核心逻辑：按列遍历，统计连续丢失长度
            # 从第1列开始（第0列是染色体号）
            for col_idx in range(1, self.n + 1):
                current_loss_count = 0
                current_chr = ''
                
                for row_idx in range(len(self.array)):
                    # 防止列对齐不齐导致的越界
                    if col_idx >= len(self.array[row_idx]): 
                        continue

                    row_data = self.array[row_idx]
                    chr_id = row_data[0]
                    val = row_data[col_idx]

                    # 初始化第一行染色体
                    if row_idx == 0:
                        current_chr = chr_id

                    # 如果染色体发生了变化 (换了一条染色体)
                    if chr_id != current_chr:
                        # 结算上一条染色体最后的丢失计数
                        if current_loss_count > 0:
                            self.all.append(current_loss_count)
                        # 重置计数器和当前染色体
                        current_loss_count = 0
                        current_chr = chr_id
                    
                    # 判断当前单元格是否为丢失 (没有数字即为丢失)
                    has_digit = re.search(r'\d+', val)
                    
                    if not has_digit:
                        # 没有数字 -> 丢失 -> 计数+1
                        current_loss_count += 1
                    else:
                        # 有数字 -> 基因存在 -> 结算之前的连续丢失
                        if current_loss_count > 0:
                            self.all.append(current_loss_count)
                        current_loss_count = 0 # 重置

                # 该列循环结束，结算最后一次计数
                if current_loss_count > 0:
                    self.all.append(current_loss_count)

            # 统计频率 (Histogram)
            self.log(f"统计完成，捕获到 {len(self.all)} 个丢失片段。")
            for item in self.all:
                self.hash[item] = self.hash.get(item, 0) + 1

            # 写入结果
            out_path = f"output/{self.output_file}"
            self.log(f"正在写入结果: {out_path}")
            
            with open(out_path, 'w', encoding='utf-8') as f:
                if not self.hash:
                    f.write("No result found.\n")
                    self.log("结果为空 (No gene loss detected).")
                else:
                    # 按丢失长度排序输出
                    for key in sorted(self.hash.keys()):
                        f.write(f"{key}\t{self.hash[key]}\n")
            self.log("写入成功。")

        except Exception as e:
            self.log(f"处理数据出错: {str(e)}")
            traceback.print_exc()
            raise e


if __name__ == '__main__':
    # 确保输出目录存在
    if not os.path.exists('output'):
        os.makedirs('output')

    # 日志文件
    log_path = 'output/debug_log.txt'
    
    with open(log_path, 'w', encoding='utf-8') as log_file:
        def log_wrapper(msg):
            print(msg)
            ts = datetime.datetime.now().strftime('%H:%M:%S')
            log_file.write(f"[{ts}] {msg}\n")
            log_file.flush() 

        log_wrapper("Script started.")
        log_wrapper(f"Current Dir: {os.getcwd()}")
        
        try:
            all_files = [f for f in os.listdir('.') if os.path.isfile(f)]
            
            input_files = []
            # 排除自身和无关文件
            ignore_list = ['lost.py', 'run.py', 'manage.py', 'debug_log.txt']
            
            for f in all_files:
                # 排除 .py, .bat, .exe, 以及 output 目录下的文件(虽然listdir一般不含子目录内容)
                if f not in ignore_list and not f.endswith(('.py', '.bat', '.exe')):
                    input_files.append(f)

            if not input_files:
                log_wrapper("Error: No input files found!")
            
            for input_file in input_files:
                log_wrapper(f"Processing file: {input_file}")
                
                file_name = os.path.splitext(input_file)[0]
                output_file_path = f"{file_name}_lost.txt"

                gene_analysis = GeneAnalysis_diushi(input_file, output_file_path, log_file)
                gene_analysis.read_input()
                gene_analysis.process_data()
            
            log_wrapper("All tasks finished successfully.")

        except Exception as e:
            log_wrapper(f"CRITICAL ERROR: {str(e)}")
            traceback.print_exc(file=log_file)
            # 【修复3】显式退出码 1，告诉调用者(views.py)这里出错了
            sys.exit(1)