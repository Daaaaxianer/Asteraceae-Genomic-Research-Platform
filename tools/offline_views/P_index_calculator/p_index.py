#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author : yuzijian1010@163.com
# @FileName : P_index.py
# @Last Time : 2026/02/06 (Optimized for Offline Desktop App Integration)

import sys
import re
import os
import traceback

# 全局变量
genome_fractionation = {}
ooo = []
uuu = []

def chr_retain(arr, buchang, cks_2, sigema_start, sigema_end):
    """
    计算单个染色体的保留率和 Sigma 值
    """
    if not arr: return []
    
    chr_name = arr[0][0]
    retain = []
    num = 0
    
    for i in range(0, len(arr), buchang):
        start = i - cks_2
        end = i + cks_2
        a = []
        num += 1
        
        # 亚基因组列对比 (j和k)
        for j in range(1, len(arr[i])):
            for k in range(j + 1, len(arr[i])):
                # 内部函数：统计窗口内的有效基因
                def get_stats(col_idx):
                    count = 0
                    total_len = 0
                    for index in range(start, end):
                        if 0 <= index < len(arr):
                            total_len += 1
                            # 只要包含数字即视为有效基因，匹配 "." 则跳过
                            val = str(arr[index][col_idx])
                            if any(c.isdigit() for c in val):
                                count += 1
                    return count, total_len

                num_1, length = get_stats(j)
                num_2, _ = get_stats(k)

                retain_1 = num_1 / length if length > 0 else 0
                retain_2 = num_2 / length if length > 0 else 0

                # 核心计算逻辑
                if retain_1 == 0 or retain_2 == 0:
                    a.append(0)
                    continue

                avg = (retain_1 + retain_2) * 0.5
                sig1 = (retain_1 - retain_2) / avg
                sig2 = (retain_2 - retain_1) / avg

                if sigema_start < sig1 < sigema_end:
                    a.append(1)
                    ooo.append(sig1)
                elif sigema_start < sig2 < sigema_end:
                    a.append(-1)
                    uuu.append(sig2)
                else:
                    a.append(0)
        retain.append(a)

    # 存储统计结果到字典
    genome_fractionation[chr_name] = [[len(arr), num], []]
    b = []
    if retain and retain[0]:
        for i in range(len(retain[0])):
            tmp = [retain[row][i] for row in range(len(retain)) if retain[row][i] != 0]
            num1 = tmp.count(1)
            num2 = tmp.count(-1)
            num0 = len(retain) - num1 - num2
            genome_fractionation[chr_name][1].extend([num1, num2, num0])
            b.append([abs(sum(tmp)), len(tmp)] if tmp else [0, 0])
    return b

def calculate_retain(file_path, sub_geno_num, buchang, cks_2, sigema_start, sigema_end):
    """
    读取文件并进行 P-index 计算的主控函数
    """
    array = []
    print(f"[*] Starting to parse file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            arr = line.split()
            
            # 门槛 1: 只要列数足够
            if len(arr) >= sub_geno_num:
                # 尝试提取第一列的数字作为染色体号，如果没有数字就用 "1"
                ch_nums = re.findall(r"\d+", arr[0])
                ch = ch_nums[0] if ch_nums else "1"
                
                # 门槛 2: 填充数据
                data_row = [ch]
                for i in range(sub_geno_num):
                    if i < len(arr):
                        data_row.append(arr[i])
                    else:
                        data_row.append(".") # 补位
                
                array.append(data_row)
    
    print(f"[*] Success! Parsed valid rows: {len(array)}")
    
    if len(array) < cks_2:
        print(f"Critical Warning: Data rows ({len(array)}) is very small.")
        if len(array) == 0:
            return 0
    
    # 按染色体号排序
    array.sort(key=lambda x: str(x[0]))
    
    all_retain = []
    temp_list = []
    for i in range(len(array)):
        temp_list.append(array[i])
        if i == len(array) - 1 or array[i][0] != array[i + 1][0]:
            res = chr_retain(temp_list, buchang, cks_2, sigema_start, sigema_end)
            if res: all_retain.append(res)
            temp_list = []
    
    print(f"-------------- {os.path.basename(file_path)} --------------")
    all_res = []
    if all_retain and len(all_retain[0]) > 0:
        for i in range(len(all_retain[0])):
            num_sum = sum(all_retain[j][i][1] for j in range(len(all_retain)))
            total_sum = sum(all_retain[j][i][0] for j in range(len(all_retain)))
            res = total_sum / num_sum if num_sum > 0 else 0
            all_res.append(res)
            if i < 4:
                print(f"Sub-pair {i+1}: {num_sum} windows calculated, score: {res:.5f}")
    
    final_p = sum(all_res) / len(all_res) if all_res else 0
    print(f"\nFinal P-index: {final_p:.6f}\n")

def Genomic_fractionation_pure(data_list, out_file):
    """
    纯 Python 实现的基因组统计，替代 Numpy 逻辑，写入结果文件
    """
    if not data_list: return
    
    try:
        with open(out_file, 'a+', encoding='utf-8') as out:
            data_list.sort(key=lambda x: x[0])
            num_cols = len(data_list[0])
            col_sums = [0] * num_cols
            for row in data_list:
                for i in range(1, num_cols):
                    col_sums[i] += row[i]
            
            a = col_sums[1] # 总基准行数
            for i in range(2, num_cols):
                curr_sum = col_sums[i]
                total_perc = (curr_sum / a * 100) if a > 0 else 0
                out.write(f"{curr_sum}({total_perc:.2f}%)\t")
                for row in data_list:
                    row_val = row[i]
                    row_total = row[1]
                    row_perc = (row_val / row_total * 100) if row_total > 0 else 0
                    out.write(f"{row_val}({row_perc:.2f}%)\t")
                out.write('\n')
            
            out.write(f"{a}\t")
            for row in data_list:
                perc = (row[1] / a * 100) if a > 0 else 0
                out.write(f"{row[1]}({perc:.2f}%)\t")
            out.write('\n')
    except Exception as e:
        print(f"Error writing to output file: {e}")

if __name__ == "__main__":
    # 参数校验
    if len(sys.argv) < 5:
        print("Usage: python P_index.py <sliding_window> <step> <sigma_start> <sigma_end>")
        sys.exit(1)

    try:
        cks = int(sys.argv[1])
        buchang = int(sys.argv[2])
        sigema_start = float(sys.argv[3])
        sigema_end = float(sys.argv[4])
        cks_2 = cks // 2
    except ValueError:
        print("Error: Invalid arguments. Please provide numeric values.")
        sys.exit(1)

    # 动态获取任务目录下的 txt 文件 (兼容 views.py 生成的 input_data.txt)
    all_files = [f for f in os.listdir('.') if f.endswith('.txt') and f not in ['pindex_result.txt', 'requirements.txt']]
    
    if not os.path.exists("output"):
        os.makedirs("output")

    for file in all_files:
        try:
            ooo.clear()
            uuu.clear()
            genome_fractionation.clear()

            calculate_retain(file, 2, buchang, cks_2, sigema_start, sigema_end)
            
            # 输出文件路径：output/input_data.txt (或其他文件名)
            output_file = os.path.join("output", os.path.basename(file))
            if os.path.exists(output_file): 
                os.remove(output_file)

            if ooo and uuu:
                ooo.sort(reverse=True)
                uuu.sort(reverse=True)
                print(f"A>B Max/Min sigma: {round(ooo[0], 5)}, {round(ooo[-1], 5)}")
                print(f"B>A Max/Min sigma: {round(uuu[0], 5)}, {round(uuu[-1], 5)}\n")

            if genome_fractionation:
                sample_key = list(genome_fractionation.keys())[0]
                col_count = len(genome_fractionation[sample_key][1])
                for j in range(0, col_count, 3):
                    new_list = []
                    for k, v in genome_fractionation.items():
                        try: k_int = int(k)
                        except: k_int = 0
                        new_list.append([k_int, v[0][1]] + v[1][j:j+3])
                    Genomic_fractionation_pure(new_list, output_file)
                    
        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")
            traceback.print_exc()