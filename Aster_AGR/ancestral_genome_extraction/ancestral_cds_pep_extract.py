import re
import os
import sys

def build_ancestor_dict():
    """构建祖先基因字典"""
    ancestor_dict = {}
    with open('ancestors_gene.txt', 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    ancestor_gene = parts[0]  # 例如: AAKI85
                    arla_gene = parts[1]     # 例如: Arla1g00003
                    
                    # 从祖先基因名中提取染色体号
                    chrom_match = re.search(r'\d+', ancestor_gene)
                    if chrom_match:
                        chrom_num = chrom_match.group()
                    else:
                        chrom_num = "0"  # 如果没有数字，使用0
                    
                    ancestor_dict[arla_gene] = (ancestor_gene, chrom_num)
    
    print(f"读取到 {len(ancestor_dict)} 个祖先基因对应关系")
    return ancestor_dict

def extract_and_rename_sequences(input_file, output_file, file_type, ancestor_dict):
    """
    提取并重命名序列文件
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        file_type: 文件类型 ('cds' 或 'pep')
        ancestor_dict: 祖先基因字典
    """
    print(f"\n处理 {file_type.upper()} 文件: {input_file}")
    
    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 {input_file}")
        return 0
    
    extracted_count = 0
    skipped_count = 0
    
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        current_header = None
        current_sequence = []
        
        for line in f_in:
            line = line.strip()
            
            if line.startswith('>'):  # 这是序列头
                # 处理前一个序列
                if current_header is not None:
                    process_sequence(current_header, ''.join(current_sequence), 
                                   f_out, ancestor_dict, file_type)
                    extracted_count += 1
                
                # 开始新序列
                current_header = line[1:]  # 去掉'>'
                current_sequence = []
            elif current_header is not None:
                # 累积序列行
                current_sequence.append(line)
        
        # 处理最后一个序列
        if current_header is not None:
            process_sequence(current_header, ''.join(current_sequence), 
                           f_out, ancestor_dict, file_type)
            extracted_count += 1
    
    print(f"从{file_type.upper()}文件中提取到 {extracted_count} 个匹配的序列")
    print(f"结果已保存到 {output_file}")
    
    return extracted_count

def process_sequence(header, sequence, output_file, ancestor_dict, file_type):
    """处理单个序列"""
    # 检查是否在祖先基因字典中
    if header in ancestor_dict:
        ancestor_gene, chrom_num = ancestor_dict[header]
        
        # 提取g及以后的内容
        # 例如：Arla1g00003 -> g00003
        g_pos = header.find('g')
        if g_pos != -1:
            # 保留从g开始的部分
            gene_suffix = header[g_pos:]  # 例如: g00003
        else:
            # 如果没有找到g，保留整个基因名
            gene_suffix = header
        
        # 创建新的基因名：祖先基因前缀 + g及以后的部分
        new_gene_name = ancestor_gene + gene_suffix
        
        # 写入输出文件
        if file_type == 'cds':
            # CDS文件通常需要保持格式，每行60个字符
            output_file.write(f'>{new_gene_name}\n')
            for i in range(0, len(sequence), 60):
                output_file.write(sequence[i:i+60] + '\n')
        else:
            # PEP文件，序列通常在一行
            output_file.write(f'>{new_gene_name}\n{sequence}\n')

def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) < 3:
        print("用法: python script.py <cds输出文件名> <pep输出文件名>")
        print("例如: python script.py AAKI.cds AAKI.pep")
        sys.exit(1)
    
    cds_output = sys.argv[1]
    pep_output = sys.argv[2]
    
    # 构建祖先基因字典
    ancestor_dict = build_ancestor_dict()
    
    if not ancestor_dict:
        print("错误: 没有读取到祖先基因对应关系")
        sys.exit(1)
    
    # 处理CDS文件
    cds_input = '../Arla_genome/Arla.cds'
    cds_count = extract_and_rename_sequences(cds_input, cds_output, 'cds', ancestor_dict)
    
    # 处理PEP文件
    pep_input = '../Arla_genome/Arla.pep'
    pep_count = extract_and_rename_sequences(pep_input, pep_output, 'pep', ancestor_dict)
    
    # 显示总结信息
    print("\n" + "="*50)
    print("处理完成！")
    print("="*50)
    print(f"CDS文件: 提取了 {cds_count} 个序列 -> {cds_output}")
    print(f"PEP文件: 提取了 {pep_count} 个序列 -> {pep_output}")
    
    # 显示一些示例
    print("\n重命名示例:")
    examples_shown = 0
    for arla_gene, (ancestor_gene, chrom_num) in ancestor_dict.items():
        if examples_shown >= 5:
            break
        
        # 提取g及以后的内容
        g_pos = arla_gene.find('g')
        if g_pos != -1:
            gene_suffix = arla_gene[g_pos:]
            new_name = ancestor_gene + gene_suffix
            print(f"  {arla_gene} -> {new_name}")
            examples_shown += 1

if __name__ == "__main__":
    main()