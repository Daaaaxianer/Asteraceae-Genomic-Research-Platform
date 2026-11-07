# -*- coding: utf-8 -*-
# @Author: wjq
# @Date:   2021-07-12 15:16:31
# @Last Modified by:   wjq
# @Last Modified time: 2024-01-03 13:09:35
"""
run ColinearScan

"""
import os
import re
import time
import glob
import subprocess
from collections import defaultdict
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

import pandas as pd


class RunBioSoftware:
    def __init__(self, num_process, num_thread):
        self.num_process = num_process
        self.num_thread = num_thread
        self.main()

    @staticmethod
    def check_file(file_path):
        n = os.path.isfile(file_path)
        file_name = os.path.basename(file_path)
        if not n:
            print(f'{file_name}---File not exist!!!')
        # assert n, "File not exist!!!"

    @staticmethod
    def check_del(file_path):
        n = os.path.isfile(file_path)
        if n:
            os.remove(file_path)

    @staticmethod
    def get_chr_num(gene):
        # chrna = re.split('[g|G|B]', gene)[0]
        # chr_num = re.sub('\\D+', '', chrna)
        # spec_na = re.findall('\\D+', chrna)[0]
        spec_na = re.findall('^\\D+', gene)[0]
        chr_num = re.search('\\d+', gene)[0]
        return [spec_na, int(chr_num)]

    @staticmethod
    def isself(pos):
        start1, start2, end1, end2 = pos
        if abs(min(start1, end1) - min(start2, end2)) < 30 and \
           abs(max(start2, end2) - max(start1, end1)) < 50:
            return 1
        else:
            return 0

    @staticmethod
    def isoverlap(pos):
        s1, e1 = min(pos[0], pos[2]), max(pos[0], pos[2])
        s2, e2 = min(pos[1], pos[3]), max(pos[1], pos[3])
        bs1, be1 = min(pos[4], pos[6]), max(pos[4], pos[6])
        bs2, be2 = min(pos[5], pos[7]), max(pos[5], pos[7])
        if s1 >= bs1-30 and e1 <= be1+30 and s2 >= bs2-50 and e2 <= be2+50:
            return 1
        else:
            return 0

    def get_lens(self, lens_path):
        lens_dit = {}
        self.check_file(lens_path)
        lens_f = open(lens_path, 'r')
        name = os.path.basename(lens_path).split('.')[0]
        for li in lens_f:
            lis = li.strip().split()
            lis[0] = str(int(lis[0]))
            lens_dit[lis[0]] = lis[1]
        chr_num = len(lens_dit.keys())

        return lens_dit, chr_num

    def get_gff(self, gff_path):
        self.check_file(gff_path)
        gff_dit = {}
        ch = {'+': '1', '-': '-1'}
        gff_f = open(gff_path, 'r')
        for li in gff_f:
            lis = li.strip().split()
            gff_dit[lis[5]] = ch[lis[3]]+' '+lis[6]
        return gff_dit

    def remove_redundancy(self, block_path, sf_path):
        block, old_flag, reason, isadd = [], [], '', 1
        block_f = open(block_path, 'r')
        sf = open(sf_path, 'a+')
        for li in block_f:
            if re.search('^\\s+', li):
                sf.write(li)
            elif any(([x in li for x in ['the', '+']])):
                sf.write(li)
            elif '>' in li:
                start = re.split('\\s+', block[0])
                end = re.split('\\s+', block[-1])
                start1, start2 = int(float(start[1])), int(float(start[3]))
                end1, end2 = int(float(end[1])), int(float(end[3]))

                for i in range(len(old_flag)):
                    pos = [start1, start2, end1, end2]
                    if self.get_chr_num(start[0])[0] == self.get_chr_num(start[2])[0]:
                        flag1 = self.isself(pos)
                        if flag1:
                            isadd, reason = 0, "self homologous"
                    lis = old_flag[i].split('\t')
                    pos.extend([int(x) for x in lis])
                    flag2 = self.isoverlap(pos)
                    if flag2:
                        isadd, reason = 0, f'overlap with block {i}+1th'
                        break
                if isadd:
                    old_flag.append(
                        '\t'.join([str(start1), str(start2), str(end1), str(end2)]))
                    for row in block:
                        sf.write(row)
                    sf.write(li)
                else:
                    sf.write(li)
                    sf.write(reason+'\n')
                    isadd = 1
                block = []
            else:
                block.append(li)

    def blast_get_pair(self, blast_path, path):
        if not os.path.isdir(path):
            os.mkdir(path)
        na1, na2 = os.path.basename(blast_path).split('.')[0].split('_')
        sf_path = f'{path}/{na1}_all_{na2}_all.pairs'
        sf = open(sf_path, 'w')
        self.check_file(blast_path)
        gff1 = self.get_gff(f'./bed/{na1}.new.gff')
        gff2 = self.get_gff(f'./bed/{na2}.new.gff')
        df = pd.read_csv(blast_path, sep='\t', names=list(
            range(1, 13)), index_col=False)
        df2 = df[(df[12].astype('float') >= 100) & (df[2] != df[1])]
        df3 = df2.loc[:, [1, 2]]
        for li in df3.values.tolist():
            flag = '\t'.join(li)
            if any(([x in flag for x in ['Un', 'Scaffold', 'random']])):
                continue
            if na1 in li[0] and na2 in li[1]:
                str1 = gff1.get(li[0], 0)
                str2 = gff2.get(li[1], 0)
                if not all((str1, str2)):
                    continue
                sf.write(f'{li[0]} {str1} {li[1]} {str2}\n')
        sf.close()
        # purged_path = open(f'{path}/{na1}_all_{na2}_all.purged', 'w')
        purged_path = f'{path}/{na1}_all_{na2}_all.purged'
        purged_save = open(purged_path, 'w')
        
        pair_path = open(sf_path)
        pair_lines = pair_path.readlines()
        count_dit = defaultdict(int)
        for pair in pair_lines:
            pairs = re.split('\\s+', pair)
            count_dit[pairs[0]] += 1
            count_dit[pairs[3]] += 1
        for pair in pair_lines:
            pairs = re.split('\\s+', pair.strip())
            if pairs[0] == pairs[1]:continue
            if count_dit[pairs[0]] >= 50 or count_dit[pairs[3]] >=50:continue
            purged_save.write(pair)
        purged_save.close()
        # p = subprocess.call(f'cat {sf_path} | repeat_mask.pl -n 50 > {purged_path}', shell=True)
        # if p != 0:
        #     print(f'Warning!!! {p}')

        lens1, chr_num1 = self.get_lens(f'./bed/{na1}.lens')
        lens2, chr_num2 = self.get_lens(f'./bed/{na2}.lens')

        if not os.path.isdir(f'{path}/pairs'):
            os.mkdir(f'{path}/pairs')
        else:
            os.system(f'rm -rf {path}/pairs')
            os.mkdir(f'{path}/pairs')
        purged_f = open(purged_path, 'r')
        for li in purged_f:
            lis = re.split('\\s+', li)
            spe1, chr1 = self.get_chr_num(lis[0])
            spe2, chr2 = self.get_chr_num(lis[3])
            sf = open(f'{path}/pairs/{spe1}.{chr1}.{spe2}.{chr2}.pair', 'a+')
            sf.write(li)
            sf.close()

        return lens1, lens2, chr_num1

    @staticmethod
    def run_colinearscan(len1, len2, pair_path, block_path):
        try:
            p = subprocess.call(f'blockscan -chr1len {len1} -chr2len '
                                f'{len2} -mg1 50 -mg2 50 {pair_path} > {block_path}',
                                shell=True)
            if p != 0:
                print(f'Warning!!! {p}')
        except Exception as e:
            print(e)

    def run(self, blast_path):
        path = os.path.basename(blast_path).split('.')[0]
        if not os.path.isdir('blk'):
            os.mkdir('blk')
        lens1, lens2, chr_num = self.blast_get_pair(blast_path, path)

        thead_pool = ThreadPoolExecutor(self.num_thread)
        files = os.listdir(f'./{path}/pairs/')
        blk_path = f'./{path}/block'
        if not os.path.isdir(blk_path):
            os.mkdir(blk_path)
        thread = []
        for file in files:
            fl = file.split('.')
            if fl[1] not in lens1 or fl[3] not in lens2: continue
            len1, len2 = lens1[fl[1]], lens2[fl[3]]
            blk_name = '.'.join(fl[:-1])+'.blk'
            pair_path, block_path = f'./{path}/pairs/{file}', f'./{path}/block/{blk_name}'
            # print(pair_path, blk_name)
            # print(len1, len2)
            # self.run_colinearscan(len1, len2, pair_path, block_path)
            handle = thead_pool.submit(self.run_colinearscan, len1, len2, pair_path, block_path)
            thread.append(handle)
        for th in as_completed(thread):
            th.result()
        thead_pool.shutdown()


        sf = f'./blk/{path}.block.rr.txt'
        self.check_del(sf)
        block_path = f'./{path}/block/'
        files = os.listdir(block_path)
        for file in files:
            try:
                file_path = os.path.join(block_path, file)
                self.remove_redundancy(file_path, sf)
            except Exception as e:
                print(f'error: {e}')

        partiallys = []
        spec1, spec2 = path.split('_')
        if spec1 == spec2:
            sf1 = f'./blk/{path}.partially.block.rr.txt'
            self.check_del(sf1)
            for i in range(1, chr_num+1):
                for j in range(i, chr_num+1):
                    partiallys.append(f'{spec1}.{i}.{spec2}.{j}.blk')
            for file in partiallys:
                file_path = os.path.join(block_path, file)
                if not os.path.isfile(file_path):
                    continue
                try:
                    self.remove_redundancy(file_path, sf1)
                except Exception as e:
                    print(f'error: {e}')

        os.system(f'rm -rf {path}')

    def main(self):
        print('start!!!')
        t1 = time.time()
        p = Pool(self.num_process)
        files = glob.glob(f'blastp/*.blast')
        for fn in files:
            p.apply_async(self.run, args=(fn,))

        p.close()
        p.join()
        t2 = time.time()
        print(f'run time:{int(t2-t1)}')
        print('end!!!')


if __name__ == '__main__':

    # default
    thread = 3
    process = 3
    RunBioSoftware(process, thread)
