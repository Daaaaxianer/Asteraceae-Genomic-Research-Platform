#run_ks.py
# -*- coding: utf-8 -*-
"""
calculata ks (Windows Compatible Version)
"""
import os
import sys
import glob
import subprocess
import shutil
from multiprocessing import Pool

class RunBioSoftware:
    def __init__(self, num_process):
        self.num_process = num_process
        self.main()

    @staticmethod
    def check_file(file_path):
        return os.path.isfile(file_path)

    def run_ks(self, path, blk, cds1, cds2):
        print(f'Processing: {path}...')
        spec1, spec2 = path.split('_')
        
        # 结果文件名
        ks_sf = f'{spec1}_{spec2}.ks.txt'
        
        # 1. 创建临时目录
        if not os.path.isdir(path):
            os.mkdir(path)
            
        # 2. 准备 CDS 文件 (替代 cp 和 cat 命令)
        combined_cds_path = ""
        
        if spec1 == spec2:
            # 同物种：复制
            combined_cds_path = os.path.join(path, f'{spec1}.cds')
            shutil.copy(cds1, combined_cds_path)
        else:
            # 不同物种：合并 (替代 cat)
            combined_cds_path = os.path.join(path, f'{spec1}_{spec2}.fasta')
            with open(combined_cds_path, 'wb') as outfile:
                for f in [cds1, cds2]:
                    with open(f, 'rb') as infile:
                        outfile.write(infile.read())
                        outfile.write(b'\n') # 确保换行

        # 3. 调用 Perl (替代 subprocess.call shell=True)
        # 注意：这里假设 perl 已经在系统 PATH 里 (tools.py 里已经配置了)
        cmd = ['perl', 'calculate.Ks.pl', path, spec1, blk, combined_cds_path, ks_sf]
        
        print(f"  Running Perl: {' '.join(cmd)}")
        
        try:
            # 使用 subprocess.run 更安全
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f'  Error in Perl script: {result.stderr}')
            else:
                print(f'  Success: {ks_sf} generated.')
        except Exception as e:
            print(f"  Execution failed: {e}")

        # 4. 清理临时目录 (替代 rm -rf)
        try:
            shutil.rmtree(path)
        except Exception:
            pass

    def main(self):
        # 寻找 block 文件 (tools.py 已经把文件重命名为 1_2.block.rr.txt)
        files = glob.glob(os.path.join('blk', '*.block.rr.txt'))
        
        if not files:
            print("No input block files found in ./blk/")
            return

        tasks = []
        for fn in files:
            if 'partially' in fn or 'less' in fn:
                continue
            
            # fn 是 blk\1_2.block.rr.txt
            basename = os.path.basename(fn)
            name = basename.split('.')[0] # 拿到 "1_2"
            parts = name.split('_')
            
            if len(parts) < 2: 
                print(f"Skipping invalid filename: {basename}")
                continue
                
            spec1, spec2 = parts[0], parts[1]
            
            # 寻找 CDS 文件
            # 优先找 .cds，找不到找 .cds.fasta
            cds1 = f'cds/{spec1}.cds'
            if not self.check_file(cds1): cds1 = f'cds/{spec1}.cds.fasta'
            
            cds2 = f'cds/{spec2}.cds'
            if not self.check_file(cds2): cds2 = f'cds/{spec2}.cds.fasta'
            
            if not self.check_file(cds1) or not self.check_file(cds2):
                print(f"Missing CDS files for {spec1} or {spec2}")
                continue

            tasks.append((name, fn, cds1, cds2))

        # Windows 下多进程如果打包可能会有问题，先尝试单线程运行看能不能跑通
        # 如果需要多进程，可以把 1 改回 self.num_process，但要注意 freeze_support
        if self.num_process > 1:
            p = Pool(self.num_process)
            for args in tasks:
                p.apply_async(self.run_ks, args=args)
            p.close()
            p.join()
        else:
            # 单线程模式 (调试更稳定)
            for args in tasks:
                self.run_ks(*args)

if __name__ == '__main__':
    # 为了稳定，先用单线程跑，确保逻辑没问题
    process = 1 
    RunBioSoftware(process)