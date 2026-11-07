import re
import os
import sys

def process_gff_files(output_filename):
    # 读取祖先基因文件
    ancestor_dict = {}
    with open('ancestors_gene.txt', 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    ancestor_gene = parts[0]  # 例如: AAKI85
                    arla_gene = parts[1]     # 例如: Arla1g00003
                    
                    # 从祖先基因名中提取染色体号
                    # 例如: AAKI85 -> 85, AAKI3 -> 3
                    chrom_match = re.search(r'\d+', ancestor_gene)
                    if chrom_match:
                        chrom_num = chrom_match.group()
                    else:
                        chrom_num = "0"  # 如果没有数字，使用0
                    
                    ancestor_dict[arla_gene] = (ancestor_gene, chrom_num)
    
    print(f"读取到 {len(ancestor_dict)} 个祖先基因对应关系")
    
    # 显示一些示例
    print("祖先基因示例:")
    for i, (arla_gene, (ancestor_gene, chrom_num)) in enumerate(ancestor_dict.items()):
        if i < 5:  # 只显示前5个示例
            print(f"  {arla_gene} -> {ancestor_gene} (染色体{chrom_num})")
    
    # 读取 GFF 文件
    input_gff = '../Arla_genome/Arla.new.gff'
    
    if not os.path.exists(input_gff):
        print(f"错误: 找不到输入文件 {input_gff}")
        return
    
    # 存储提取的基因行，按染色体分组
    chromosomes_data = {}
    
    with open(input_gff, 'r') as f:
        line_number = 0
        extracted_count = 0
        for line in f:
            line_number += 1
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            if len(parts) < 7:
                continue
            
            gene_name = parts[5]  # 第六列是基因名
            
            # 检查是否在祖先基因字典中
            if gene_name in ancestor_dict:
                ancestor_gene, chrom_num = ancestor_dict[gene_name]
                
                # 创建修改后的行
                modified_parts = parts.copy()
                
                # 提取g及以后的内容
                # 例如：Arla1g00003 -> g00003
                # 找到第一个'g'的位置
                g_pos = gene_name.find('g')
                if g_pos != -1:
                    # 保留从g开始的部分
                    gene_suffix = gene_name[g_pos:]  # 例如: g00003
                else:
                    # 如果没有找到g，保留整个基因名
                    gene_suffix = gene_name
                
                # 创建新的基因名：祖先基因前缀 + g及以后的部分
                new_gene_name = ancestor_gene + gene_suffix
                modified_parts[5] = new_gene_name
                
                # 第一列替换为从祖先基因中提取的染色体号
                modified_parts[0] = chrom_num
                
                # 按染色体分组存储
                if chrom_num not in chromosomes_data:
                    chromosomes_data[chrom_num] = []
                chromosomes_data[chrom_num].append(modified_parts)
                extracted_count += 1
    
    print(f"从GFF文件中提取到 {extracted_count} 个匹配的基因")
    
    if extracted_count == 0:
        print("警告: 没有找到匹配的基因！请检查基因名是否匹配。")
        return
    
    # 重新编号并写入输出文件
    with open(output_filename, 'w') as f:
        # 按染色体号排序（数字排序）
        sorted_chromosomes = sorted(chromosomes_data.keys(), 
                                  key=lambda x: int(x) if x.isdigit() else x)
        
        total_genes = 0
        for chrom_num in sorted_chromosomes:
            genes = chromosomes_data[chrom_num]
            # 按原始顺序保持，但重新编号第七列
            for i, gene_parts in enumerate(genes, 1):
                gene_parts[6] = str(i)  # 第七列重新从1开始编号
                f.write('\t'.join(gene_parts) + '\n')
            total_genes += len(genes)
    
    print(f"处理完成！结果已保存到 {output_filename}")
    
    # 显示统计信息
    print("\n统计信息:")
    for chrom_num in sorted_chromosomes:
        genes = chromosomes_data[chrom_num]
        print(f"  染色体 {chrom_num}: {len(genes)} 个基因")
    
    # 显示一些示例
    print("\n基因重命名示例:")
    for chrom_num in sorted_chromosomes[:3]:  # 只显示前三个染色体
        genes = chromosomes_data[chrom_num]
        for i, gene_parts in enumerate(genes[:2]):  # 每个染色体显示前2个
            if i == 0:
                print(f"\n  染色体 {chrom_num}:")
            # 找到对应的原始基因名
            original_gene = ""
            for key, (ancestor, chrom) in ancestor_dict.items():
                # 重构新基因名进行比较
                g_pos = key.find('g')
                if g_pos != -1:
                    gene_suffix = key[g_pos:]
                    expected_new_name = ancestor + gene_suffix
                    if expected_new_name == gene_parts[5]:
                        original_gene = key
                        break
            
            if original_gene:
                print(f"    {original_gene} -> {gene_parts[5]}")
            else:
                print(f"    新基因名: {gene_parts[5]}")
            print(f"    染色体号: {gene_parts[0]}, 新编号: {gene_parts[6]}")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python script.py <输出文件名>")
        print("例如: python script.py AAKI.new.gff")
        sys.exit(1)
    
    output_filename = sys.argv[1]
    process_gff_files(output_filename)