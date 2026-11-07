# -*- coding: utf-8 -*-
# @Author: wjq
# @Date:   2021-07-12 15:16:31
# @Last Modified by:   wjq
# @Last Modified time: 2021-09-22 23:24:55
"""
Calculate Ks (and Ka) for the gene pairs in ColinearScan blocks.

Input : <blk-dir>/<sp1>_<sp2>.block.rr.txt   blocks from 2_block/run_colinearscan.py
        <cds-dir>/<sp>.cds                   CDS FASTA of each species
                                             (<sp>.cds.fasta is also accepted)
Output: <ks-dir>/<sp1>_<sp2>.ks.txt          id1  id2  Dn  Ds  (-2 = not calculated)

For every gene pair the CDS are translated, aligned with ClustalW2 and back-translated
(calculate_ks.pl); Ka/Ks values come from SeqStatistics.pm (BioPerl).

Requires Perl with BioPerl, and `clustalw2` on your PATH (see the README).

Example:
    python run_ks.py --blk-dir blk --cds-dir cds --ks-dir ks --processes 12
"""
import argparse
import glob
import os
import shutil
import subprocess
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))


class RunBioSoftware:
    def __init__(self, num_process, blk_dir='blk', cds_dir='cds', ks_dir='ks'):
        self.num_process = num_process
        self.blk_dir = blk_dir
        self.cds_dir = cds_dir
        self.ks_dir = ks_dir
        self.main()

    @staticmethod
    def check_file(file_path):
        return os.path.isfile(file_path)

    def cds_file(self, spec):
        """<sp>.cds, or <sp>.cds.fasta if that is what exists."""
        path = f'{self.cds_dir}/{spec}.cds'
        if self.check_file(path):
            return path
        return f'{self.cds_dir}/{spec}.cds.fasta'

    def run_ks(self, name, blk, cds1, cds2):
        print('start!!!', name)
        spec1, spec2 = name.split('_')
        ks_sf = f'{self.ks_dir}/{spec1}_{spec2}.ks.txt'
        # temporary directory for the ClustalW files; removed afterwards
        tmp = os.path.join(self.ks_dir, '.tmp', name)
        os.makedirs(tmp, exist_ok=True)
        if spec1 == spec2:
            cds_f = f'{tmp}/{spec1}.cds'
            shutil.copy(cds1, cds_f)
        else:
            cds_f = f'{tmp}/{spec1}_{spec2}.fasta'
            with open(cds_f, 'wb') as out:
                for fn in (cds1, cds2):
                    with open(fn, 'rb') as fh:
                        shutil.copyfileobj(fh, out)

        p = subprocess.call(['perl', os.path.join(HERE, 'calculate_ks.pl'),
                             tmp, spec1, blk, cds_f, ks_sf])
        if p != 0:
            print(f'Warning!!! {name}: calculate_ks.pl exited with {p}')
        shutil.rmtree(tmp, ignore_errors=True)

    def main(self):
        os.makedirs(self.ks_dir, exist_ok=True)
        p = Pool(self.num_process)
        jobs = []
        for fn in sorted(glob.glob(f'{self.blk_dir}/*.block.rr.txt')):
            if 'partially' in fn or 'less' in fn:
                continue
            name = os.path.basename(fn).split('.')[0]
            spec1, spec2 = name.split('_')
            cds1, cds2 = self.cds_file(spec1), self.cds_file(spec2)
            jobs.append(p.apply_async(self.run_ks, args=(name, fn, cds1, cds2)))

        p.close()
        p.join()
        for job in jobs:
            job.get()  # re-raise errors from the workers instead of failing silently
        shutil.rmtree(os.path.join(self.ks_dir, '.tmp'), ignore_errors=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Calculate Ks for the gene pairs in ColinearScan blocks.')
    ap.add_argument('--blk-dir', default='blk', help='directory with {sp1}_{sp2}.block.rr.txt [default: blk]')
    ap.add_argument('--cds-dir', default='cds', help='directory with {sp}.cds [default: cds]')
    ap.add_argument('--ks-dir', default='ks', help='output directory [default: ks]')
    ap.add_argument('--processes', type=int, default=12, help='species pairs run in parallel [default: 12]')
    args = ap.parse_args()
    RunBioSoftware(args.processes, args.blk_dir, args.cds_dir, args.ks_dir)
