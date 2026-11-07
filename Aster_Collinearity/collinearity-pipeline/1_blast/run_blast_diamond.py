# -*- coding: utf-8 -*-
# @Author: wjq
# @Date:   2021-07-12 15:16:31
# @Last Modified by:   wjq
# @Last Modified time: 2022-02-15 19:11:19
"""
Run all-vs-all protein BLAST (BLASTP) or DIAMOND for a set of species.

Input : <species>.pep   protein FASTA files in the current directory
Output: <spec1>_<spec2>.blast (BLASTP) or <spec1>_<spec2>.diamond (DIAMOND),
        tabular format (outfmt 6), query = spec1, database = spec2.

By default every ordered pair is run, so the forward (A_B), reverse (B_A) and
self (A_A) comparisons are all produced.

Examples
--------
    # all pairs of every *.pep in the current directory, BLASTP
    python run_blast_diamond.py

    # DIAMOND, 4 jobs in parallel with 8 threads each
    python run_blast_diamond.py --program diamond --processes 4 --threads 8

    # only the listed pairs
    python run_blast_diamond.py --pairs Elu_Ddev Ddev_Elu Elu_Elu Ddev_Ddev

    # compare one new species against all others (both directions)
    python run_blast_diamond.py --add-species Tpr
"""
import argparse
import glob
import itertools
import subprocess
import time
from multiprocessing import Pool


class RunBioSoftware:
    def __init__(self, spec, repeat, align, noalign, flag, num_process, thread):
        self.species = spec
        self.repeat = repeat
        self.subs = align
        self.nosubs = noalign
        self.flag = flag
        self.num_process = num_process
        self.thread = thread
        self.main()

    def run_blast(self, pair):
        spec1, spec2 = pair.split('_')
        p = subprocess.call(f'blastp -query {spec1}.pep -out {pair}.blast -db {spec2}.db'
                            f' -outfmt 6 -evalue 1e-5 -max_target_seqs 10 -num_threads '
                            f'{self.thread}', shell=True)
        if p != 0:
            print(f'Warning!!! {pair}: blastp exited with {p}')

    def run_diamond(self, pair):
        spec1, spec2 = pair.split('_')
        p = subprocess.call(f'diamond blastp -d {spec2}.nr -q {spec1}.pep -e 1e-5 -f 6 '
                            f'-p {self.thread} -o {pair}.diamond -k 50', shell=True)
        if p != 0:
            print(f'Warning!!! {pair}: diamond exited with {p}')

    def get_spec(self):
        spec = []
        for pair in self.subs:
            spec.extend(pair.split('_'))
        return list(set(spec))

    def get_pair(self):
        if self.repeat:
            # all ordered pairs, including A_A and both A_B and B_A
            pairs = list(itertools.product(self.species, repeat=2))
        else:
            # each unordered pair once, no self comparison
            pairs = list(itertools.combinations(self.species, 2))
        return ['_'.join(pa) for pa in pairs]

    def remove_sub(self):
        new_sub = []
        for pair in self.subs:
            if pair not in self.nosubs:
                new_sub.append(pair)
        self.subs = new_sub

    def main(self):
        p = Pool(self.num_process)
        if self.subs:
            self.species = self.get_spec()
        else:
            self.subs = self.get_pair()

        if self.nosubs:
            self.remove_sub()

        jobs = []
        if self.flag == 'blast':
            for s in self.species:
                subprocess.call(f'makeblastdb -in {s}.pep -dbtype prot -out {s}.db', shell=True)
            run = self.run_blast
        else:
            for s in self.species:
                subprocess.call(f'diamond makedb --in {s}.pep --db {s}.nr', shell=True)
            run = self.run_diamond

        for pair in self.subs:
            timestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f'run ------------------------------{pair}--{timestr}')
            jobs.append(p.apply_async(run, args=(pair,)))

        p.close()
        p.join()
        for job in jobs:
            job.get()  # re-raise errors from the workers instead of failing silently


def parse_args():
    ap = argparse.ArgumentParser(description='All-vs-all BLASTP / DIAMOND for *.pep files in the current directory.')
    ap.add_argument('--program', choices=['blast', 'diamond'], default='blast',
                    help='search program [default: blast]')
    ap.add_argument('--processes', type=int, default=10, help='number of pairs run in parallel [default: 10]')
    ap.add_argument('--threads', type=int, default=8, help='threads per search [default: 8]')
    ap.add_argument('--no-repeat', action='store_true',
                    help='run each unordered pair once (A_B but not B_A) and skip self comparisons')
    ap.add_argument('--pairs', nargs='*', default=[], metavar='A_B',
                    help='run only these pairs (query_database); default: all pairs')
    ap.add_argument('--exclude', nargs='*', default=[], metavar='A_B', help='pairs to skip')
    ap.add_argument('--add-species', nargs='*', default=[], metavar='SP',
                    help='run each of these species against all other species, in both directions')
    return ap.parse_args()


if __name__ == '__main__':
    args = parse_args()

    # every <species>.pep in the current directory
    species = sorted(fn.split('.')[0] for fn in glob.glob('*.pep'))
    sub = list(args.pairs)

    for na in args.add_species:
        for spec in species:
            sub.append(f'{na}_{spec}')
            sub.append(f'{spec}_{na}')
    sub = list(set(sub))

    RunBioSoftware(species, not args.no_repeat, sub, args.exclude, args.program,
                   args.processes, args.threads)
