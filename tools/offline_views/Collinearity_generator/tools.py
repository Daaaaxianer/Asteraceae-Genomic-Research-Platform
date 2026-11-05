import os
import glob
import pandas as pd
import sys
import traceback
from functools import reduce
from django.conf import settings

# =========================================================
# 1. 路径配置
# =========================================================
try:
    BASE_DIR = settings.BASE_DIR
    FILE_KEEP_DIR = os.path.join(BASE_DIR, 'file_keep')
except:
    # 本地测试兼容逻辑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    FILE_KEEP_DIR = os.path.join(os.path.dirname(current_dir), 'file_keep')

# =========================================================
# 2. 核心清洗与工具函数
# =========================================================

def read_data_file(file_path):
    """
    读取文件，针对 Vvi_Lal.txt 这种不规则文件做了特别优化
    使用 names=range(200) 防止列数不一致导致的数据丢失
    """
    parsers = [("\t", "Tab"), (r"\s+", "Whitespace"), (",", "Comma")]
    for sep, name in parsers:
        try:
            # 宽容模式读取：强制读取前200列，且全部视为字符串
            df = pd.read_csv(file_path, sep=sep, header=None, comment='#', 
                           names=range(200), dtype=str)
            
            # 初步清洗：删除全为空(NaN)的列
            df = df.dropna(axis=1, how='all')
            
            if not df.empty and df.shape[1] > 0:
                # 清洗第一列（Key列），去除首尾空格
                df[0] = df[0].astype(str).str.strip()
                return df
        except Exception:
            continue
            
    return pd.DataFrame()

def is_valid_gene(val):
    """
    单值判断：判断一个单元格的值是否像基因
    """
    s = str(val).strip()
    if s in [".", "nan", "", "None", "NAN", "<NA>"]:
        return False
    # 排除纯数字 (如 0, 1, 4)
    if s.isdigit():
        return False
    # 排除单字符（根据你的数据，基因名至少2个字符）
    if len(s) < 2:
        return False
    return True

def is_junk_column(series):
    """
    整列判断：判断这一列是否是垃圾列（数字列或空列）
    针对 Vvi_Lal.txt 的数字列(4)和空列进行过滤
    """
    # 转为字符串并去空
    s = series.astype(str).str.strip()
    
    # 1. 提取非空内容（排除 ., nan, 空串）
    valid_content = s[~s.isin([".", "nan", "", "None", "NAN"])]
    
    # 如果除去点和空之后没剩啥了，说明这列全是空白，删！
    if valid_content.empty:
        return True
        
    # 2. 检查是否是纯数字 (针对 Vvi_Mtr.txt 的 '1', '2' 等)
    # 逻辑：如果非空内容中，超过 80% 都是纯数字，则判定为垃圾列
    is_digit = valid_content.str.match(r'^-?\d+(\.\d+)?$')
    if is_digit.mean() > 0.8: 
        return True
        
    return False

def find_reference_file(work_dir, reference_name_input):
    """查找参考文件，包含安全修复"""
    # 安全修正：只取文件名，忽略路径，防止 ../../ 攻击
    safe_name = os.path.basename(reference_name_input)
    
    # 1. 精确匹配
    exact_path = os.path.join(work_dir, safe_name)
    if os.path.exists(exact_path): return exact_path
    
    # 2. 尝试加 .txt
    if os.path.exists(exact_path + ".txt"): return exact_path + ".txt"
    
    # 3. 模糊搜索 (智能匹配前缀)
    base_search = safe_name.split('.')[0]
    files = glob.glob(os.path.join(work_dir, "*"))
    for f in files:
        fname = os.path.basename(f)
        # 跳过系统生成的文件
        if fname.startswith("result_") or fname in ["output.txt", "error_log.txt"] or fname.endswith(".zip"): 
            continue
        if base_search in fname: 
            return f
    return None

# =========================================================
# 3. 核心处理逻辑 (通用)
# =========================================================

def process_file_list(file_list, pvu_file):
    """
    通用的文件读取与清洗逻辑
    输入：文件路径列表
    输出：清洗干净、重命名好的 DataFrame 列表
    """
    dfs_to_merge = []
    abs_ref = os.path.abspath(pvu_file)

    for file in file_list:
        # 跳过参考文件自身
        if os.path.abspath(file) == abs_ref: continue
        
        df = read_data_file(file)
        if df.empty: continue

        # --- 核心清洗：列级过滤 ---
        valid_cols = []
        for c in df.columns:
            if c == 0: # 永远保留 Key 列 (第0列)
                valid_cols.append(c)
            else:
                # 只有非垃圾列才保留
                if not is_junk_column(df[c]):
                    valid_cols.append(c)
        
        # 如果只剩 Key 列，说明其他全是垃圾数据，没必要合并
        if len(valid_cols) < 2: continue 
        df = df[valid_cols]
        # ------------------------

        # 重命名列 (除了key)，格式：文件名_原有列名
        fname = os.path.basename(file)
        new_cols = {0: 'merge_key'}
        for c in df.columns:
            if c != 0: new_cols[c] = f"{fname}_{c}"
        df = df.rename(columns=new_cols)
        
        dfs_to_merge.append(df)
    
    return dfs_to_merge

# =========================================================
# 4. 业务模式 (1:2 和 1:3)
# =========================================================

def collinearity_generator_run_two(file_list, pvu_file, output_file, species_name):
    print(f"Running 1:2 Mode. Ref: {os.path.basename(pvu_file)}")
    
    # 1. 读取并清洗输入文件
    dfs_to_merge = process_file_list(file_list, pvu_file)

    if not dfs_to_merge:
        data = pd.DataFrame(columns=['merge_key'])
    else:
        # Outer Join 保证所有基因都不丢失
        data = reduce(lambda left, right: pd.merge(left, right, on='merge_key', how='outer'), dfs_to_merge)

    data = data.fillna(".")

    # 2. 处理参考文件 (1:2 模式只取 Key 和 Ref1)
    pvu_df = read_data_file(pvu_file)
    # 补齐列防止报错
    if pvu_df.shape[1] < 2: pvu_df[1] = "."
    pvu_df = pvu_df.iloc[:, [0, 1]] # 强制只取前两列
    pvu_df.columns = ['merge_key', 'ref_col']
    pvu_df['merge_key'] = pvu_df['merge_key'].astype(str).str.strip()

    # 3. 最终合并
    final_df = pd.merge(pvu_df, data, on='merge_key', how='left').fillna(".")

    # 4. 生成 Expanded 列
    data_cols = [c for c in final_df.columns if c not in ['merge_key', 'ref_col']]
    data_part = final_df[data_cols]
    
    def combine_row(row):
        # 提取有效基因
        vals = [str(x).strip() for x in row if is_valid_gene(x)]
        # ★ 关键修改：用逗号连接，避免 TSV 双引号问题 ★
        return ','.join(vals) if vals else "."

    if not data_part.empty:
        final_df['expanded'] = data_part.apply(combine_row, axis=1)
    else:
        final_df['expanded'] = "."

    # 5. 输出
    output_cols = ['merge_key'] + data_cols + ['ref_col', 'expanded']
    final_df = final_df[output_cols]
    final_df.to_csv(output_file, index=False, header=False, sep="\t")


def collinearity_generator_run_three(file_list, pvu_file, output_file, species_name):
    print(f"Running 1:3 Mode. Ref: {os.path.basename(pvu_file)}")
    
    # 1. 读取并清洗
    dfs_to_merge = process_file_list(file_list, pvu_file)

    if not dfs_to_merge:
        data = pd.DataFrame(columns=['merge_key'])
    else:
        data = reduce(lambda left, right: pd.merge(left, right, on='merge_key', how='outer'), dfs_to_merge)

    data = data.fillna(".")
    
    # 2. 处理参考文件 (1:3 模式取 Key, Ref1, Ref2)
    pvu_df = read_data_file(pvu_file)
    while pvu_df.shape[1] < 3: 
        pvu_df[pvu_df.shape[1]] = "."
    pvu_df = pvu_df.iloc[:, [0, 1, 2]] # 强制只取前三列
    pvu_df.columns = ['merge_key', 'ref_1', 'ref_2']
    pvu_df['merge_key'] = pvu_df['merge_key'].astype(str).str.strip()
    
    # 3. 最终合并
    final_df = pd.merge(pvu_df, data, on='merge_key', how='left').fillna(".")
    
    # 4. 生成 Expanded
    data_cols = [c for c in final_df.columns if c not in ['merge_key', 'ref_1', 'ref_2']]
    data_part = final_df[data_cols]

    def combine_row(row):
        vals = [str(x).strip() for x in row if is_valid_gene(x)]
        return ','.join(vals) if vals else "."

    if not data_part.empty:
        final_df['expanded'] = data_part.apply(combine_row, axis=1)
    else:
        final_df['expanded'] = "."

    # 5. 输出
    output_cols = ['merge_key'] + data_cols + ['ref_1', 'ref_2', 'expanded']
    final_df = final_df[output_cols]
    final_df.to_csv(output_file, index=False, header=False, sep="\t")

# =========================================================
# 5. 主入口
# =========================================================

def collinearity_generator_run_tools(place, patten, reference_file, species_name):
    work_dir = os.path.join(FILE_KEEP_DIR, place)
    output_path = os.path.join(work_dir, "output.txt")
    
    try:
        ref_path = find_reference_file(work_dir, reference_file)
        if not ref_path:
            # 找不到参考文件时，列出当前目录文件方便调试
            files = os.listdir(work_dir)
            raise FileNotFoundError(f"Reference file '{reference_file}' not found. Available: {files}")

        input_file_list = []
        abs_ref = os.path.abspath(ref_path)
        
        # 扫描所有文件
        for f in glob.glob(os.path.join(work_dir, "*")):
            abs_f = os.path.abspath(f)
            if abs_f == abs_ref: continue 
            fname = os.path.basename(f)
            # 排除掉输出文件和压缩包
            if fname.startswith("result_") or fname in ["output.txt", "error_log.txt"] or fname.endswith(".zip"): 
                continue
            if os.path.isfile(f):
                input_file_list.append(f)

        if patten == "two":
            collinearity_generator_run_two(input_file_list, ref_path, output_path, species_name)
        else:
            collinearity_generator_run_three(input_file_list, ref_path, output_path, species_name)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        # 将错误信息写入 output.txt，这样用户下载 zip 包后能看到报错原因
        with open(output_path, 'w') as f:
            f.write(f"Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")
        raise e