#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import glob
from django.conf import settings

def block_number_count_run_tools(task_id):
    """
    核心统计逻辑 (纯 Python 实现，无 Pandas 依赖)
    """
    # 获取工作目录
    base_dir = str(settings.BASE_DIR)
    work_dir = os.path.join(base_dir, 'file_keep', task_id)
    
    # 定义输出文件
    output_file_path = os.path.join(work_dir, 'block.all.count.txt')
    
    # 获取所有上传的文件 (排除可能存在的系统文件)
    all_files = [f for f in glob.glob(os.path.join(work_dir, '*')) if os.path.isfile(f)]
    
    results = []

    # === 业务逻辑开始 ===
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        
        # 跳过自身输出文件或非文本文件
        if file_name == 'block.all.count.txt': continue

        try:
            line_count = 0
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 示例逻辑：统计非空行数 (相当于统计 Block 数量)
                # 您可以根据实际的 Block 文件格式修改此处的逻辑
                # 例如：if line.startswith('Alignment'): count += 1
                for line in f:
                    if line.strip(): 
                        line_count += 1
            
            results.append(f"{file_name}\t{line_count}")
            
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
    # === 业务逻辑结束 ===

    # 写入结果
    with open(output_file_path, 'w', encoding='utf-8') as f_out:
        f_out.write("File_Name\tBlock_Count\n") # 表头
        for row in results:
            f_out.write(row + "\n")
            
    return output_file_path