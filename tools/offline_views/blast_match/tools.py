import os
import random
import string
import subprocess

path_get = os.getcwd()

# ----------------- 基础文件操作 -----------------

def name_set():
    """在 file_keep 中创建随机文件夹"""
    c = ''.join(random.sample(string.digits, 9))
    target_dir = os.path.join(path_get, 'file_keep', c)
    from api.download_access import create_job_directory
    create_job_directory(target_dir)
    return c

def keep_file(na, c, fg=None):
    """保存上传的文件到指定文件夹"""
    if fg is not None:
        nam = na.name.split(".")
        na.name = nam[0] # 简单的重命名逻辑，可根据需要调整

    file_dir = os.path.join(path_get, 'file_keep', c)
    file_path = os.path.join(file_dir, na.name)

    with open(file_path, 'wb+') as f:
        for chunk in na.chunks():
            f.write(chunk)

# ----------------- 核心业务逻辑 -----------------

def blast_choose_match(place, myFile1, identity, score):
    """
    筛选 Blast 结果 (outfmt 6)
    Column 2: Identity (%)
    Column 11: Bit Score
    """
    work_dir = os.path.join(path_get, 'file_keep', place)
    input_path = os.path.join(work_dir, myFile1)
    output_fasta_path = os.path.join(work_dir, 'result_2.fasta')
    output_seq_path = os.path.join(work_dir, 'sequence.txt')

    # 确保文件存在
    if not os.path.exists(input_path):
        # 创建空文件防止报错
        open(output_fasta_path, 'w').close()
        open(output_seq_path, 'w').close()
        return

    gather = set()
    
    with open(input_path, 'r') as pbl_fasta, \
         open(output_fasta_path, 'w') as blast_file:
        
        for line in pbl_fasta:
            parts = line.split()
            if len(parts) < 12: # 确保行结构完整
                continue
                
            # outfmt 6 标准: col 3 is identity (index 2), col 12 is bitscore (index 11)
            try:
                curr_iden = float(parts[2])
                curr_score = float(parts[11])
                
                # 执行筛选
                if curr_iden >= float(identity) and curr_score >= float(score):
                    blast_file.write(line)
                    gather.add(parts[1]) # parts[1] 通常是 subject id (sseqid)
            except ValueError:
                continue

    # 写入提取的 ID 列表
    with open(output_seq_path, 'w') as sequence_file:
        for item in gather:
            sequence_file.write(item + '\n')


def blast_match_run_tools(place, patten, species_data, e, score, identity, nucl_or_prot):
    """
    构造并执行 Blast 命令
    """
    work_dir = os.path.join(path_get, 'file_keep', place)
    db_path = os.path.join(path_get, 'static', 'blast_match_database', nucl_or_prot, f"{species_data}")
    
    # 构造命令
    # 注意: max_target_seqs 1 表示只取最佳匹配
    cmd = [
        patten, # blastp 或 blastn
        "-query", "1.fasta",
        "-db", db_path,
        "-outfmt", "6",
        "-evalue", str(e),
        "-out", "result.txt",
        "-num_threads", "8",
        "-max_target_seqs", "1"
    ]

    try:
        # 使用 subprocess.run 替代 os.system
        # cwd 参数指定命令在 work_dir 目录下运行，这样 output 文件会直接生成在那里
        subprocess.run(cmd, cwd=work_dir, check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"Blast run error: {error_msg}")
        # 这里可以选择抛出异常，让 View 层捕获
        raise RuntimeError(f"Blast failed: {error_msg}")

    # 执行筛选
    blast_choose_match(place=place, myFile1="result.txt", identity=identity, score=score)