# tools.py
import os
import sys
import shutil
import subprocess
import traceback
import re
from django.conf import settings

# 获取 tools.py 所在的目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = "/usr/bin/python"

def extract_number(text):
    """从字符串末尾提取数字"""
    match = re.search(r'(\d+)$', text)
    if match:
        return int(match.group(1))
    return None

def normalize_and_rank_gff(lens_path, gff_path):
    """
    1. 修正 Chromosome ID (如 1 -> Adu01)
    2. 【核心修复】将物理坐标转换为 Rank，并同时更新 Start(Col3), End(Col4) 和 Column 7 (如果存在)
    """
    try:
        filename = os.path.basename(gff_path)
        print(f"Processing GFF: {filename} (ID Normalization + Rank Conversion)")
        
        # 1. 读取 Lens ID
        lens_map = {} 
        valid_ids = set()
        
        with open(lens_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    lens_id = parts[0]
                    valid_ids.add(lens_id)
                    num = extract_number(lens_id)
                    if num is not None:
                        lens_map[num] = lens_id
        
        # 2. 读取 GFF 数据
        gff_data = []
        with open(gff_path, 'r') as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) < 4: continue
                
                # --- 新增：确保基因 ID 没有多余空格 ---
                parts[1] = parts[1].strip() 
                # -----------------------------------

                chrom = parts[0]
                try:
                    start = int(parts[2]) 
                    gff_data.append({
                        'chrom': chrom,
                        'start': start,
                        'parts': parts
                    })
                except ValueError:
                    # 增加错误打印，方便调试
                    print(f"Skipping line (ValueError): {line.strip()}")
                    continue

        # 3. 修正 ID 并分组
        for item in gff_data:
            orig_chrom = item['chrom']
            final_chrom = orig_chrom
            if orig_chrom not in valid_ids:
                c_num = extract_number(orig_chrom)
                if c_num is not None and c_num in lens_map:
                    final_chrom = lens_map[c_num]
            
            item['final_chrom'] = final_chrom
            item['parts'][0] = final_chrom

        # 4. 排序并生成 Rank
        gff_data.sort(key=lambda x: (x['final_chrom'], x['start']))
        
        current_chrom = None
        rank_counter = 0
        rewritten_lines = []
        
        for item in gff_data:
            chrom = item['final_chrom']
            if chrom != current_chrom:
                current_chrom = chrom
                rank_counter = 0
            
            rank_counter += 1
            
            # --- 【关键修改】 ---
            # 【修复点 2】：不要覆盖 parts[1] (基因名)！
            # 将 Rank 写入 parts[2] (Start) 和 parts[3] (End)
            
            if len(item['parts']) >= 4:
                item['parts'][2] = str(rank_counter)     # Start -> Rank
                item['parts'][3] = str(rank_counter + 1) # End -> Rank + 1
            
            # 2. 更新 Column 7 (针对 User Special 模式, 索引为6)
            if len(item['parts']) > 6:
                item['parts'][6] = str(rank_counter)
            # -------------------
            
            rewritten_lines.append("\t".join(item['parts']) + "\n")

        # 5. 写入
        temp_gff = gff_path + ".tmp"
        with open(temp_gff, 'w') as f:
            for line in rewritten_lines:
                f.write(line)
        
        shutil.move(temp_gff, gff_path)
        print(f"✅ GFF Processed: Updated {len(rewritten_lines)} genes (Cols 3,4,7 updated)")
            
    except Exception as e:
        print(f"⚠️ GFF Processing Error: {e}")
        traceback.print_exc()

def zu_block_dotplot_run_tools(place, name1, name2, block_num):
    work_dir = os.path.join(settings.BASE_DIR, 'file_keep', place)
    
    if not os.path.exists(work_dir):
        print(f"❌ Error: Work directory does not exist: {work_dir}")
        return

    script_source_path = os.path.join(CURRENT_DIR, 'dotplot_block.2400.pd.py')
    if not os.path.exists(script_source_path):
        print(f"❌ Error: Script not found at {script_source_path}")
        return

    script_dest_path = os.path.join(work_dir, 'dotplot_block.2400.pd.py')
    try:
        shutil.copy(script_source_path, script_dest_path)
    except Exception as e:
        print(f"Error copying script: {e}")
        return

    # === 执行 ID 修正 + 坐标转换 ===
    print(">>> Starting data cleanup (ID correction and rank conversion)...")
    # 注意：这里调用的是同一文件上方的 normalize_and_rank_gff
    normalize_and_rank_gff(os.path.join(work_dir, f"{name1}.lens"), os.path.join(work_dir, f"{name1}.new.gff"))
    normalize_and_rank_gff(os.path.join(work_dir, f"{name2}.lens"), os.path.join(work_dir, f"{name2}.new.gff"))
    print(">>> Data cleanup complete.")
    # ===============================

    cmd = f"{PYTHON_EXE} dotplot_block.2400.pd.py {name1} {name2} {block_num}"
    print(f"Running command: {cmd}")

    try:
        # 使用 subprocess.run 运行脚本
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # --- 【核心修改】无论成功失败，都打印输出 ---
        print("----------- Script STDOUT -----------")
        print(result.stdout)
        print("----------- Script STDERR -----------")
        print(result.stderr)
        print("-------------------------------------")

        if result.returncode != 0:
            print("❌ Script Execution Failed!")
        else:
            print("✅ Script Execution Successful.")

        if result.returncode != 0:
            raise Exception(f"The plotting script failed. Error log:\n{result.stderr}")

    except Exception as e:
        print(f"Exception during subprocess: {e}")
        traceback.print_exc()