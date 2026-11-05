import sys
import os

# 确保能找到 func_
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from functools import reduce
from func_ import *


class run_circos():
    def __init__(self,options,format):
        self.savefig = 'savefig'
        self.specieslist = 'specieslist list'
        self.lens_file = 'lens hmm_model'
        self.gff_file = 'gff hmm_model'
        self.pair_file = 'pair hmm_model'
        self.format = format
        self.linecolor = 'blue'
        self.linewidth = '0.8'
        self.alpha = '0.8'
        self.GAP_RATIO = '4'
        self.labelscolor = 'black'
        self.gene_pair_lens = 5
        self.label_pos = '1.1'
        self.axes_limit = 0.5
        self.dpi = '300'
        for k, v in options:
            setattr(self, str(k), v)
        self.specieslist = [chr.upper() for chr in self.specieslist.split(',')]

        self.fpchrolen = open(self.lens_file,'r')
        self.fpgff = open(self.gff_file,'r')
        self.alphagenepairs = open(self.pair_file,'r')

        figure(1, (8, 8))
        self.root =axes([0, 0, 1, 1])

        specieslist,self.iscompletegenome = get_species_and_chr(self.specieslist)
        self.chro2len,self.labels = get_chr_lenth(self.specieslist,self.fpchrolen,self.iscompletegenome)
        self.gene2pos,self.gene2chain,self.gene_labels = input_gff(self.fpgff)

        self.fullchrolen = reduce(add,list(self.chro2len.values()))
        self.chr_number = len(self.labels)
        self.GAP = self.fullchrolen/int(self.GAP_RATIO)/self.chr_number
        self.total_size = self.fullchrolen + self.chr_number * self.GAP

        self.start_list = [0]*self.chr_number
        for i in range(1, self.chr_number):
            self.start_list[i] = self.start_list[i-1] + self.chro2len[self.labels[i-1]] + self.GAP
        self.stop_list = [(self.start_list[i] + self.chro2len[self.labels[i]]) for i in range(self.chr_number)]

    def run(self):
        rowno = 0
        if self.format=='processed':
            self.result = self.processed()
        elif self.format=='blast':
            self.result = self.blast_()
        elif self.format=='mcscan':
            self.result = self.mcscan_()
        elif self.format=='colinearscan':
            self.result = self.colinearscan_()
        for ids in self.result:
            if len(ids)==2:
                id1,id2 = ids
            else:
                id1, id2, self.linecolor = ids
            try:
                pos1 = self.gene2pos[id1]
                pos2 = self.gene2pos[id2]
                chro1 = self.gene_labels[id1]
                chro2 = self.gene_labels[id2]
                order1 = self.labels.index(chro1)
                order2 = self.labels.index(chro2)
                self.plot_bez_inner((order1, pos1, radius_a), (order2, pos2, radius_a), self.linecolor)
                rowno = rowno + 1
            except:
                pass
        j = 0
        for start, stop in zip(self.start_list, self.stop_list):
            start, stop = to_radian(start, self.total_size), to_radian(stop, self.total_size)

            plot_arc(start, stop, radius_a)
            plot_arc(start, stop, radius_b)

            plot_cap(start, clockwise=False)
            plot_cap(stop)

            label_x, label_y = rad_to_coord((start + stop) / 2, radius_b * float(self.label_pos))
            text(label_x, label_y, self.labels[j], horizontalalignment="center", verticalalignment="center", fontsize=7,
                 color=self.labelscolor)
            j += 1

        for i in range(self.chr_number):
            pos = 0
            while pos < self.chro2len[self.labels[i]]:
                xx1, yy1 = self.transform_pt(i, int(pos), radius_b)
                xx2, yy2 = self.transform_pt(i, int(pos), radius_b - 0.003)
                plot([xx1, xx2], [yy1, yy2], "k-", lw=.2)
                pos = pos + 10000000

        self.root.set_xlim(-float(self.axes_limit), float(self.axes_limit))
        self.root.set_ylim(-float(self.axes_limit), float(self.axes_limit))
        self.root.set_axis_off()
        savefig(self.savefig, dpi=float(self.dpi))

    def processed(self):
        for row in self.alphagenepairs:
            lis = row.split()
            if len(lis) == 3:
                id1, id2, self.linecolor = lis
                yield [id1,id2,self.linecolor]
            else:
                id1, id2 = lis
                yield [id1,id2]
        self.alphagenepairs.close()

    def blast_(self):
        for row in self.alphagenepairs:
            lis = row.split()
            if float(lis[-2])<= 0 and float(lis[-2])>0.05:
                continue
            id1 = lis[0]
            id2 = lis[0]
            yield [id1,id2]
        self.alphagenepairs.close()

    def mcscan_(self):
        flag = False
        for row in self.alphagenepairs:
            if '#' in row and 'Alignment' not in row:
                continue
            if 'Alignment' in row:
                e, N = re.findall('e_value=(.*?)\sN=(\d+)', row)[0]
                if float(e) <= 0 or float(e) > 0.01 or int(N) < int(self.gene_pair_lens):
                    flag = False
                    continue
                else:
                    flag = True
                    continue
            if flag:
                rows = row.split('\t')[1:3]
                yield rows

        self.alphagenepairs.close()

    def colinearscan_(self):
        da = self.alphagenepairs.read()
        blocks = re.findall('(the \d+th path length \d+\n[\s\S]+?)\n\n', da)
        for block in blocks:
            lis = block.split('\n')
            lenth = re.findall('the \d+th path length (\d+)', lis[0])[0]
            p = re.findall('>LOCALE p-value : (\d+.\d+)', lis[-1])[0]
            if int(lenth) < int(self.gene_pair_lens) or float(p) <= 0 or float(p) > 0.05:
                continue
            else:
                for idline in lis[1:-1]:
                    id1 = idline.split(' ')[0]
                    id2 = idline.split(' ')[2]
                    yield [id1,id2]
        self.alphagenepairs.close()

    def transform_pt(self,ch, pos, r):
        rad = to_radian(pos + self.start_list[ch], self.total_size)
        return r * cos(rad), r * sin(rad)

    def plot_bez_inner(self,p1, p2,cl):
        a, b, c = p1
        ex1x, ex1y = self.transform_pt(a, b, c)
        a, b, c = p2
        ex2x, ex2y = self.transform_pt(a, b, c)
        ratio = .5
        x = [ex1x, ex1x * ratio, ex2x * ratio, ex2x]
        y = [ex1y, ex1y * ratio, ex2y * ratio, ex2y]
        step = .01
        t = arange(0, 1 + step, step)
        xt = Bezier(x, t)
        yt = Bezier(y, t)
        plot(xt, yt, '-', color=cl, lw=float(self.linewidth), alpha=float(self.alpha))
