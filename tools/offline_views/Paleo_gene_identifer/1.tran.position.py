#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yuzijian1010@163.com
# @FileName :1.tran.position.py
# @Time :2023/6/1 10:21
import re
import sys


species1 = sys.argv[1]  # 获取第一个物种名字
species2 = sys.argv[2]  # 获取第二个物种名字

lens1file = f"{species1}.lens"  #gene pair
LEN1 = open(lens1file, "r") 
lens2file = f"{species2}.lens"
LEN2 = open(lens2file, "r")
position = f"{species1}_{species2}.txt"
POS = open(position, 'r')
outfile = f"{species1}_{species2}.corr.txt"
OUT = open(outfile, "w")


pix_start_1 = 200  # Start pixel
pix_start_2 = 200  # Start pixel
end_add = 0
############################
hash_lens1 = {}
hash_pix1 = {}
hash_pix_start1 = {}
temp = None
nu = 0

for line in LEN1:
    line = line.strip()
    array = line.split()
    hash_lens1[array[0]] = array[1]
    nu += 1
    if nu == 1:
        hash_pix_start1[array[0]] = pix_start_1
    else:
        hash_pix_start1[array[0]] = temp
    temp = array[2]
    pix_length = int(array[2]) - int(hash_pix_start1[array[0]])
    hash_pix1[array[0]] = pix_length
LEN1.close()


hash_lens2 = {}
hash_pix2 = {}
hash_pix_start2 = {}
tmp = None
num = 0
if lens1file == lens2file:
    hash_lens2 = hash_lens1.copy()
    hash_pix2 = hash_pix1.copy()
    hash_pix_start2 = hash_pix_start1.copy()
else:
    with open(lens2file) as LEN2:
        for line in LEN2:
            line = line.strip()
            array = line.split()
            hash_lens2[array[0]] = array[1]
            num += 1
            if num == 1:
                hash_pix_start2[array[0]] = pix_start_2
            else:
                hash_pix_start2[array[0]] = tmp
            tmp = array[2]
            pix_length = int(array[2]) -int( hash_pix_start2[array[0]])
            hash_pix2[array[0]] = pix_length
LEN2.close()


chr_length = None  #单染色体总长
chr_vir_len = None
start = None
end = None
temp_a = 1
temp_b = 1
item_a = None


for line in POS:
    temp_a = ()
    num = 0
    line = line.strip()
    array = line.split()
    for i in range(len(array)):
        arr = array[i].split(':') #A:Pp08:461-3227:Vv3:0-1104
        if not re.match(r'A\d$', arr[0]):
            print(f"\n\n\nWarning:\n{array[i]}\n{arr[0]} is wrong!\tplease check your position file...\n")
            exit()
        if arr[1] not in hash_lens1:
            print(f"\n\n\nWarning:\n{array[i]}\n{arr[1]} is wrong!\tplease check your file...\n")
            exit()
        num += 1
        if num == 1:
            temp_a = arr[1]
        item_a = arr[1]
        if temp_a != item_a:
            print(f" \n\n\nWarning:\nlast:\t{array[i-1]}\nnow:\t{array[i]}\na_last: {temp_a}\ta_now: {item_a}\n{item_a} is wrong!\tplease check your position file...\n")
            exit()
        temp_a = arr[1]
        chr_length = hash_lens1[arr[1]]
        if re.search(r'[a-zA-Z]', arr[2]):
            print(f"\n\n\nWarning:\n{array[i]}\n{arr[2]} is wrong!\tplease check your file...\n")
            exit()
        ar_a = arr[2].split('-')
        chr_vir_len = hash_pix1[arr[1]]
        if ar_a[0] == '0':
            start = 0
        elif re.match(r'0\.\d', ar_a[0]):
            start = int(float(ar_a[0]) * chr_length)
        elif re.match(r'\d\/\d$', ar_a[0]):
            start = int(eval(ar_a[0]) * chr_length)
        else:
            if re.search(r'\.|\||\\', ar_a[0]):
                print(f"\n\n\nWarning:\n{ar_a[0]} is wrong!\tplease check your position file...\n")
                exit()
            vir_seg_a = int(ar_a[0]) - int(hash_pix_start1[arr[1]])
            if vir_seg_a >= chr_vir_len:
                print(f"\n\n\nWarning:\n{array[i]}\n{arr[2]}\n{ar_a[0]}\tthere are promble!...\nvir_seg/chr_vir_len>=1\n")
                exit()
            start = int(float(vir_seg_a / chr_vir_len) * float(chr_length))
        if ar_a[1] == '1':
            end = int(chr_length) + int(end_add)
        elif re.match(r'0\.\d', ar_a[1]):
            end = int(float(ar_a[1]) * chr_length + 0.5)
        elif re.match(r'\d\/\d$', ar_a[1]):
            end = int(eval(ar_a[1]) * chr_length + 0.5)
        else:
            if re.search(r'\.|\||\\', ar_a[1]):
                print(f"\n\n\nWarning:\n{ar_a[1]} is wrong!\tplease check your position file...\n")
                exit()
            vir_seg_a = int(ar_a[1]) - int(hash_pix_start1[arr[1]])
            if vir_seg_a > chr_vir_len:
                print(f"\n\n\nWarning:\n{array[i]}\n{arr[2]}\n{ar_a[1]}\tthere are promble!...\nvir_seg/chr_vir_len>1\n")
                exit()
            if vir_seg_a == chr_vir_len:
                end = chr_length + end_add
            else:
                end = int(float(vir_seg_a / chr_vir_len) * float(chr_length) + 0.5)

        postion_a=f"{start}-{end}"
        if start<0 or end<0 or start >= end:
            print(f"\n\n\nWarning:\n{array[i]}\n{arr[0]}:{arr[1]}:{arr[2]} has something wrong!\npostion_a:{postion_a}\tplease check your position file...\n")
            exit()
        if arr[3] not in hash_lens2:
            print(f"\n\n\nWarning:\n{array[i]}\n{arr[3]} is wrong!\tplease check your file...\n")
            exit()
        chr_length=hash_lens2[arr[3]]
        if re.search(r'[a-zA-Z]', arr[4]):
            print(f"\n\n\nWarning:\n{array[i]}\n{arr[4]} is wrong!\tplease check your file...\n")
            exit()
        ar_b = arr[4].split('-')
        chr_vir_len=hash_pix2[arr[3]]
        if ar_b[0] == '0':
            start = 0
        elif re.match(r'0\.\d', ar_b[0]):
            start = int(float(ar_b[0]) * chr_length)
        elif re.match(r'\d\/\d$', ar_b[0]):
            start = int(eval(ar_b[0]) * chr_length)
        else:
            if re.search(r'\.|\||\\', ar_b[0]):
                print(f"\n\n\nWarning:\n{ar_b[0]} is wrong!\tplease check your position file...\n")
                exit()
            vir_seg_b = int(ar_b[0]) - int(hash_pix_start2[arr[3]])
            if vir_seg_b >= chr_vir_len:
                print(f"\n\n\nWarning:\n{array[i]}\n{arr[4]}\n{ar_b[0]}\tthere are promble!...\nvir_seg/chr_vir_len>=1\n")
                exit()
            start = int(float(vir_seg_b / chr_vir_len) * float(chr_length))
        if ar_b[1] == '1':
            end = int(chr_length) + int(end_add)
        elif re.match(r'0\.\d', ar_b[1]):
            end = int(float(ar_b[1]) * chr_length + 0.5)
        elif re.match(r'\d\/\d$', ar_b[1]):
            end = int(eval(ar_b[1]) * chr_length + 0.5)
        else:
            if re.search(r'\.|\||\\', ar_b[1]):
                print(f"\n\n\nWarning:\n{ar_b[1]} is wrong!\tplease check your position file...\n")
                exit()
            vir_seg_b = int(ar_b[1]) - int(hash_pix_start2[arr[3]])
            if vir_seg_b > chr_vir_len:
                print(f"\n\n\nWarning:\n{array[i]}\n{arr[4]}\n{ar_b[1]}\tthere are promble!...\nvir_seg/chr_vir_len>1\n")
                exit()
            if vir_seg_b == chr_vir_len:
                end = chr_length + end_add
            else:
                end = int(float(vir_seg_b / chr_vir_len) * float(chr_length) + 0.5)
        postion_b=f"{start}-{end}"
        if start<0 or end<0 or start >= end:
            print(f"\n\n\nWarning:\n{array[i]}\n{arr[3]}:{arr[4]} has something wrong!\npostion_b:{postion_b}\tplease check your position file...\n")
            exit()
        if i==len(array)-1:
            OUT.write(f"{arr[0]}:{arr[1]}:{postion_a}:{arr[3]}:{postion_b}\n")
        else:
            OUT.write(f"{arr[0]}:{arr[1]}:{postion_a}:{arr[3]}:{postion_b}\t")
        print(f"{arr[0]}:{arr[1]}:{postion_a}:{arr[3]}:{postion_b}")

OUT.close()
POS.close()
