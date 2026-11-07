import sys

def extract_genes_from_file(input_file, output_file):
    extracted_genes = []
    
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    if not lines:
        return 0
    
    # 获取列数（基于第一行）
    first_line = lines[0].strip().split('\t')
    total_columns = len(first_line)
    other_columns = total_columns - 2  # 前两列之外的列数
    
    # 根据其他列数确定阈值
    if other_columns > 2:
        threshold = 3  # 非"."的基因个数大于3
        need_greater = True
    else:
        threshold = 2  # 非"."的基因个数大于等于2
        need_greater = False
    
    # 处理每一行
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        parts = line.split('\t')
        if len(parts) < 3:  # 至少要有前两列和一些其他列
            continue
            
        # 第一列和第二列的基因名
        gene_col1 = parts[0]  # 第一列基因名
        gene_col2 = parts[1]  # 第二列基因名
        
        # 统计非"."的基因个数（从第三列开始）
        count_non_dot = 0
        for i in range(2, len(parts)):
            if parts[i] != '.' and parts[i] != '':
                count_non_dot += 1
        
        # 根据条件判断是否提取该基因
        if need_greater:
            # 其他列数 > 2，需要 count_non_dot > 3
            if count_non_dot > threshold:
                extracted_genes.append((gene_col1, gene_col2))
        else:
            # 其他列数 ≤ 2，需要 count_non_dot ≥ 2
            if count_non_dot >= threshold:
                extracted_genes.append((gene_col1, gene_col2))
    
    # 将提取的基因写入输出文件
    with open(output_file, 'w') as f:
        for gene1, gene2 in extracted_genes:
            f.write(f"{gene1}\t{gene2}\n")
    
    return len(extracted_genes)

# 使用示例
if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python ancestral_gene_extract.py <输入文件> [输出文件]")
        print("例如: python ancestral_gene_extract.py Arla_AAKI_order.txt ancestors_gene.txt")
        print("注意: 如果只提供一个参数，输出文件默认为'ancestors_gene.txt'")
        sys.exit(1)
    
    # 获取命令行参数
    input_file = sys.argv[1]
    
    # 如果有第二个参数，使用它作为输出文件，否则使用默认值
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = "ancestors_gene.txt"
    
    # 执行提取
    num_extracted = extract_genes_from_file(input_file, output_file)
    print(f"从 {input_file} 中提取完成！")
    print(f"共提取了 {num_extracted} 个基因对")
    print(f"结果已保存到 {output_file}")
    print(f"输出格式：第一列基因名\t第二列基因名")