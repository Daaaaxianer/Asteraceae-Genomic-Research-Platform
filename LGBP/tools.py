#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author :yzj
# @FileName :tools.py
# @Time :2022/1/14 22:04
# Written by Yu Zijian
# E-main: yuzijian1010@163.com

import os
import re
import time
import glob
import sys
import site
import csv
import json
import pylab
import random
import shutil
import string
import pymysql
import subprocess
import sysconfig
import importlib.util
import numpy as np
import pandas as pd
from ete3 import Tree
from Bio import SeqIO, Phylo, Entrez
from .email import youjian
from functools import reduce
from django.http import HttpResponse
from django.core.files import File
from django.shortcuts import render
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures
from django import forms


path_get = os.getcwd()


def get_real_python_executable():
    current_executable = sys.executable
    if 'uwsgi' not in current_executable.lower():
        return current_executable

    candidate_roots = []
    for root in (sys.exec_prefix, sys.prefix):
        if root and root not in candidate_roots:
            candidate_roots.append(root)

    for root in candidate_roots:
        for relative_path in ('bin/python3', 'bin/python', 'Scripts/python.exe'):
            python_path = os.path.join(root, relative_path)
            if os.path.exists(python_path):
                return python_path

    return shutil.which('python3') or shutil.which('python') or current_executable


def get_tool_executable(executable_name):
    direct_match = shutil.which(executable_name)
    if direct_match:
        return direct_match

    candidate_paths = []
    executable_dirs = [
        os.path.dirname(sys.executable),
        os.path.dirname(get_real_python_executable()),
    ]

    for root in (sys.exec_prefix, sys.prefix):
        if root:
            executable_dirs.append(os.path.join(root, 'bin'))
            executable_dirs.append(os.path.join(root, 'Scripts'))

    scripts_dir = sysconfig.get_path('scripts')
    if scripts_dir:
        executable_dirs.append(scripts_dir)

    user_base = getattr(site, 'USER_BASE', None)
    if user_base:
        executable_dirs.append(os.path.join(user_base, 'bin'))
        executable_dirs.append(os.path.join(user_base, 'Scripts'))

    # uWSGI deployments may not inherit a full PATH, so probe common script locations explicitly.
    executable_dirs.extend([
        os.path.expanduser('~/.local/bin'),
        '/usr/local/bin',
        '/usr/bin',
        '/bin',
    ])

    seen_dirs = set()
    for directory in executable_dirs:
        normalized_dir = os.path.normpath(directory)
        if normalized_dir in seen_dirs:
            continue
        seen_dirs.add(normalized_dir)
        candidate_paths.append(os.path.join(normalized_dir, executable_name))
        candidate_paths.append(os.path.join(normalized_dir, f'{executable_name}.exe'))

    for candidate_path in candidate_paths:
        if os.path.isfile(candidate_path) and os.access(candidate_path, os.X_OK):
            return candidate_path

    raise FileNotFoundError(
        f"Executable '{executable_name}' was not found in PATH or the active virtual environment."
    )


def has_importable_module(module_name):
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _python_can_import_module(python_executable, module_name, env=None):
    if not python_executable:
        return False
    try:
        completed = subprocess.run(
            [
                python_executable,
                '-c',
                (
                    'import importlib.util, sys; '
                    f'sys.exit(0 if importlib.util.find_spec({module_name!r}) else 1)'
                ),
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=20,
        )
        return completed.returncode == 0
    except Exception:
        return False


def get_wgdi_command(subcommand, env=None):
    """Return a WGDI command that uses the same Python environment as the web app.

    Prefer ``python -c 'from wgdi.run import main; main()'`` over the global
    ``/usr/local/bin/wgdi`` entry point.  The global entry point can be bound to
    a different Python interpreter and then fail with ``No module named wgdi``.
    """
    python_executable = get_real_python_executable()
    if _python_can_import_module(python_executable, 'wgdi.run', env=env):
        return [
            python_executable,
            '-c',
            'from wgdi.run import main; main()',
            subcommand,
            'ath.conf',
        ]

    try:
        return [get_tool_executable('wgdi'), subcommand, 'ath.conf']
    except FileNotFoundError as executable_error:
        raise FileNotFoundError(
            "WGDI is not available. Install it into the Asteraceae virtual "
            "environment, for example: "
            "/www/server/pyporject_evn/Asteraceae_venv/bin/python -m pip install --no-user wgdi"
        ) from executable_error


def get_wgdi_subprocess_env():
    env = os.environ.copy()
    mafft_root = '/www/tools/mafft-7.525-with-extensions'
    system_paths = [
        '/usr/local/sbin',
        '/usr/local/bin',
        '/usr/sbin',
        '/usr/bin',
        '/sbin',
        '/bin',
    ]
    tool_paths = [
        os.path.join(mafft_root, 'scripts'),
        os.path.join(mafft_root, 'binaries'),
        os.path.join(mafft_root, 'core'),
    ]
    env['MAFFT_BINARIES'] = os.path.join(mafft_root, 'core')
    current_paths = [item for item in env.get('PATH', '').split(os.pathsep) if item]
    merged_paths = []
    for item in tool_paths + system_paths + current_paths:
        if item not in merged_paths:
            merged_paths.append(item)
    env['PATH'] = os.pathsep.join(merged_paths)

    # Only for the WGDI subprocess: allow a user-site WGDI installation if the
    # package is not installed inside the virtual environment yet.
    # This does not change Django's own import behavior.
    env.pop('PYTHONNOUSERSITE', None)
    try:
        user_site = site.getusersitepackages()
    except Exception:
        user_site = None
    pythonpath_items = []
    if user_site and os.path.isdir(user_site):
        pythonpath_items.append(user_site)
    pythonpath_items.extend([item for item in env.get('PYTHONPATH', '').split(os.pathsep) if item])
    if pythonpath_items:
        merged_pythonpath = []
        for item in pythonpath_items:
            if item and item not in merged_pythonpath:
                merged_pythonpath.append(item)
        env['PYTHONPATH'] = os.pathsep.join(merged_pythonpath)

    return env


def run_wgdi_subcommand(place, subcommand, timeout_seconds=600):
    work_dir = os.path.join(path_get, 'file_keep', place)
    env = get_wgdi_subprocess_env()
    command = get_wgdi_command(subcommand, env=env)
    try:
        subprocess.run(
            command,
            cwd=work_dir,
            check=True,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.strip() if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr.strip() if isinstance(exc.stderr, str) else ""
        raise RuntimeError(
            f"WGDI command timed out after {timeout_seconds} seconds.\n"
            f"Command: {' '.join(command)}\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}"
        )
    except subprocess.CalledProcessError as exc:
        stdout = exc.stdout.strip() if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr.strip() if isinstance(exc.stderr, str) else ""
        raise RuntimeError(
            f"WGDI command failed with exit code {exc.returncode}.\n"
            f"Command: {' '.join(command)}\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}"
        )


# 在文件夹内 创建文件夹
def keep_in_file(na, c, fg=None):
    cmd = '''
        cd %s/file_keep/%s
        mkdir all_file
    ''' % (path_get, c)
    os.system(cmd)

    with open('%s' % os.path.join(f'{path_get}/file_keep/{c}/all_file/', na.name), 'wb') as f:
        for chunk1 in na.chunks():
            f.write(chunk1)
    f.close()


# 保存单个文件
def keep_file(na, c, fg=None):
    if fg is None:
        pass
    else:
        nam = na.name.split(".")
        na.name = nam[0]

    # 被我保存到本地啦，保存到哪里随意啦
    with open(f"{path_get}/file_keep/{c}/{na.name}", 'wb+') as f:
        for chunk1 in na.chunks():
            f.write(chunk1)
    f.close()


# 创建conf配置文件
def text_create(name, msg, place):
    desktop_path = f"{path_get}/file_keep/{place}/"  # 新创建的txt文件的存放路径
    full_path = desktop_path + name + '.conf'  # 也可以创建一个.doc的word文档
    file = open(full_path, 'w')
    file.write(msg)  # msg也就是下面的Hello world!
    file.close()


# 保存多个文件
# def keep_files(na, c, fg=None, ret_files=None):
#     cmd = f'''
#         cd {path_get}/file_keep/{c}
#         mkdir orthomcl
#     '''
#     os.system(cmd)
#
#     for file in na:
#         with open('%s' % os.path.join(f'{path_get}/file_keep/{c}/orthomcl/', file.name), 'wb') as f:
#             for i in file.chunks():
#                 f.write(i)
def keep_files(na, c):
    destination_path = os.path.join(path_get, 'file_keep', c, 'orthomcl')
    os.makedirs(destination_path, exist_ok=True)

    for file in na:
        destination_file_path = os.path.join(destination_path, file.name)
        with open(destination_file_path, 'wb') as destination_file, file.open('rb') as source_file:
            shutil.copyfileobj(source_file, destination_file)


# 此模块用于检查 文件是否存在 （b，c，d 参数未补全）
#     e ：文件夹名字
def name_check(e):
    """
    此模块用于检查 文件是否存在 （b，c，d 参数未补全）
    e ：文件夹名字
    """
    global path_get

    a = os.path.isfile('/home/a123123/PycharmProjects/untitled2/file_keep/%s/1.FASTA' % e)
    b = os.path.isfile('/home/a123123/PycharmProjects/untitled2/file_keep/%s/email.txt' % e)
    c = os.path.isfile('/home/a123123/PycharmProjects/untitled2/file_keep/%s/email.txt' % e)
    d = os.path.isfile('/home/a123123/PycharmProjects/untitled2/file_keep/%s/email.txt' % e)
    n = ''
    if b:
        n = '1.FASTA'
    elif a:
        n = 'd'
    elif a:
        n = 'd'
    elif a:
        n = 'd'
    return n


def name_set():
    """ 在file_keep中创建文件夹
    :return: c 随机文件夹名字
    """
    c = ''.join(random.sample(string.digits, 9))
    file_keep_dir = os.path.join(path_get, 'file_keep')
    os.makedirs(file_keep_dir, exist_ok=True)
    from api.download_access import create_job_directory
    create_job_directory(os.path.join(file_keep_dir, c))
    return c


# 保存邮件地址
def keep_email(e, address):
    with open(f'{path_get}/file_keep/{e}/email.txt', 'w') as f:
        f.write(address)


def read_email(place):
    global path_get
    with open(f'{path_get}/file_keep/{place}/email.txt', 'r+') as f:
        return f.read()


def zip_file(place, email, files):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        zip -r result.zip {files}
    """
    os.system(cmd)

    g = f'{path_get}/file_keep/{place}/result.zip'
    youjian(a=email, b=g, place=place)


# ================================= gfca start  =============================================


# index 保存邮件地址
def keep_email_index(place, name, email, message):
    with open(f'{path_get}/file_keep/{place}/advise.txt', 'w+') as f:
        f.write(name + '\n')
        f.write(email + '\n')
        f.write(message + '\n')

    g = f'{path_get}/file_keep/{place}/advise.txt'
    youjian(a="1457634627@qq.com", b=g, place=place)


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# blast和diamond 初筛
def blast_choose(place, myFile1, myFile2, identity, score):
    blast_file = open(f'{path_get}/file_keep/{place}/{myFile1}_{myFile2}.fasta', 'w')
    sequence_file = open(f'{path_get}/file_keep/{place}/sequence.txt', 'w')
    pbl_fasta = open(f'{path_get}/file_keep/{place}/result_2.fasta', 'r')
    gather = set()
    for line in pbl_fasta.readlines():
        ind, sco = line.split()[2], line.split()[11]
        if float(ind) >= float(identity):
            if float(sco) >= float(score):
                blast_file.write(line)
                gather.add(line.split()[1])
    for line in gather:
        sequence_file.write(line + '\n')


# blast
def blast_run_tools(place, patten, e, score, identity, myFile1, myFile2, nucl_or_prot):
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        makeblastdb -in 1.fasta -dbtype {nucl_or_prot} -parse_seqids -out dbname
        {patten} -query 2.fasta -db dbname -outfmt 6 -evalue {e} -out result_2.fasta -num_threads 8
    """
    os.system(cmd)
    blast_choose(place=place, myFile1=myFile1, myFile2=myFile2, identity=identity, score=score)


# diamond
def diamond_run_tools(place, patten, e, score, identity, myFile1, myFile2):
    cmd = f"""
    source /etc/profile
    cd {path_get}/file_keep/{place}
    diamond makedb --in 1.fasta -d nr
    diamond {patten} -d nr -q 2.fasta -o result_2.fasta -e {e} -b 2.0 --index-chunks 1
"""
    os.system(cmd)
    blast_choose(place=place, myFile1=myFile1, myFile2=myFile2, identity=identity, score=score)


# blast_初筛_match_blast
def blast_choose_match(place, myFile1, identity, score):
    blast_file = open(f'{path_get}/file_keep/{place}/result_2.fasta', 'w')
    sequence_file = open(f'{path_get}/file_keep/{place}/sequence.txt', 'w')
    pbl_fasta = open(f'{path_get}/file_keep/{place}/{myFile1}', 'r')
    gather = set()
    for line in pbl_fasta.readlines():
        ind, sco = line.split()[2], line.split()[11]
        if float(ind) >= float(identity):
            if float(sco) >= float(score):
                blast_file.write(line)
                gather.add(line.split()[1])
    for line in gather:
        sequence_file.write(line + '\n')


# blast_match
def blast_match_run_tools(place, patten, species_data, e, score, identity, nucl_or_prot):
    cmd = f"""
source /etc/profile
cd {path_get}/file_keep/{place}
{patten} -query 1.fasta -db {path_get}/static/blast_match_database/{nucl_or_prot}/{species_data}.db -outfmt 6 -evalue {e} -out result.txt -num_threads 8 -max_target_seqs 1
    """
    os.system(cmd)
    blast_choose_match(place=place, myFile1="result.txt", identity=identity, score=score)



# mcscanx
def mcscanx_run_tools(place, file_name):
    from tools.command_safety import mcscanx
    return mcscanx(place, file_name)


# colinearscan
def colinearscan_run_tools(place, score, e_value, hitnum, pos_order, cdsvchr, blast_name, gff1_name, gff2_name, file_name):
    # perl ../programs/run_colinearscan.pl ZM-OS.filter.blast 1e-5 0 30 ZM.gff OS.gff order n ZM_OS
    work_dir = os.path.join(path_get, 'file_keep', place)
    script_path = os.path.join(path_get, 'file_keep', 'programs', 'run_colinearscan.pl')
    env = os.environ.copy()
    system_paths = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
    current_path = env.get('PATH') or ''
    env['PATH'] = f"/www/tools/ColinearScan/bin:{system_paths}"
    if current_path:
        env['PATH'] = f"{env['PATH']}:{current_path}"

    cmd = [
        '/usr/bin/perl',
        script_path,
        str(blast_name),
        str(e_value),
        str(score),
        str(hitnum),
        str(gff1_name),
        str(gff2_name),
        str(pos_order),
        str(cdsvchr),
        str(file_name),
    ]
    try:
        subprocess.run(
            cmd,
            cwd=work_dir,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stdout_text = (exc.stdout or '').strip()
        stderr_text = (exc.stderr or '').strip()
        error_parts = [f"ColinearScan failed with exit code {exc.returncode}."]
        if stdout_text:
            error_parts.append(f"STDOUT:\n{stdout_text}")
        if stderr_text:
            error_parts.append(f"STDERR:\n{stderr_text}")
        raise RuntimeError("\n\n".join(error_parts)) from exc


# WGDI ---wgdi_共线性分析---
def wgdimcs_run_tools(place, evalue, score):
    write_txt = (str("[collinearity]") + "\n" + str("gff1 =  11.gff") + "\n" + str("gff2 =  22.gff") + "\n" +
                 str("lens1 = 11.len") + "\n" + str("lens2 = 22.len") + "\n" + str(f"blast = diamond.fasta") + "\n" +
                 str("blast_reverse = false") + "\n" + str("multiple  = 1") + "\n" + str("process = 8") + "\n" +
                 str(f"evalue = {evalue}") + "\n" + str(f"score = {score}") + "\n" + str("grading = 50,40,25") + "\n" +
                 str("mg = 40,40") + "\n" + str("pvalue = 0.2") + "\n" + str("repeat_number = 10") + "\n" +
                 str("position = order") + "\n" + str("savefile = result.collinearity.txt") + "\n" + "\n"
                 )
    text_create('ath', str(write_txt), place)

    run_wgdi_subcommand(place, '-icl')


# dupgen_finder_run
def dupgen_finder_run_tools(place, patten, target, outgroup):
    if patten == 'general':
        cmd = f"""
            source /etc/profile
            cd {path_get}/file_keep/{place}
            mv {target}* ../programs/dupgen_finder/data/
            cd ../programs/dupgen_finder
            perl DupGen_finder.pl -i data -t {target} -c {outgroup} -o results
            zip -r result.zip results/
            mv result.zip {path_get}/file_keep/{place}
            rm -rf data/*
            rm -rf result*
        """
        os.system(cmd)

        # g = f'{path_get}/file_keep/{place}/result.zip'
        # youjian(a=email, b=g, place=place)

    else:
        cmd = f"""
            source /etc/profile
            cd {path_get}/file_keep/{place}
            mv {target}* ../programs/dupgen_finder/data/
            cd ../programs/dupgen_finder
            perl DupGen_finder-unique.pl -i data -t {target} -c {outgroup} -o results
            zip -r result.zip results/
            mv result.zip {path_get}/file_keep/{place}
            rm -rf data/*
            rm -rf result*
        """
        os.system(cmd)

        # g = f'{path_get}/file_keep/{place}/result.zip'
        # youjian(a=email, b=g, place=place)


# paraAT
def paraat_run_tools(place, patten):
    from tools.command_safety import paraat
    return paraat(place, patten)


# kaks_calculator
def kaks_calculator_run_tools(place, patten):
    from tools.command_safety import kaks
    return kaks(place, patten)


# kaks_calculator
def zu_ks_calculate_run_tools(place):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        cp ../programs/run_ks_pro/* .
        mkdir cds
        mv *.cds cds
        mkdir blk
        mv *.txt blk
        mkdir ks
        python3 run_ks.py
    """
    subprocess.run(cmd, shell=True, check=True)


# WGDI ---wgdi_ks计算---
def get_fasta_record_ids(fasta_path):
    record_ids = set()
    with open(fasta_path, 'r', encoding='utf-8', errors='ignore') as fasta_file:
        for line in fasta_file:
            if line.startswith('>'):
                parts = line[1:].strip().split()
                if parts:
                    record_ids.add(parts[0])
    return record_ids


def _ks_gene_id_aliases(value):
    """Return common aliases for a FASTA/GFF gene ID.

    This makes the Ks step tolerant to small naming differences such as
    gene.1, gene.t1, gene-p1, gene:xxx, or pipe-separated FASTA IDs.
    """
    value = str(value or '').strip().strip('"').strip("'")
    value = value.strip(';,()[]{}<>')
    if not value:
        return set()

    aliases = {value}
    cleaned = re.sub(r'^(gene|transcript|rna|mrna|cds|protein|pep|id):', '', value, flags=re.IGNORECASE)
    aliases.add(cleaned)

    patterns = [
        r'([._-](t|p|mrna|rna|cds|protein|pep)\d*)$',
        r'([._-](RA|RB|RC|RD|RE|PA|PB|PC|PD|PE))$',
        r'(\.\d+)$',
    ]
    changed = True
    while changed:
        changed = False
        for item in list(aliases):
            for pattern in patterns:
                stripped = re.sub(pattern, '', item, flags=re.IGNORECASE)
                if stripped and stripped not in aliases:
                    aliases.add(stripped)
                    changed = True

    more_aliases = set()
    for item in aliases:
        for token in re.split(r'[|,;\s]+', item):
            token = token.strip().strip(';,()[]{}<>')
            if token:
                more_aliases.add(token)
                more_aliases.add(re.sub(r'^(gene|transcript|rna|mrna|cds|protein|pep|id):', '', token, flags=re.IGNORECASE))
    aliases.update(item for item in more_aliases if item)
    return aliases


def _build_ks_alias_map(valid_ids):
    alias_to_real = {}
    ambiguous_aliases = set()
    for real_id in valid_ids:
        for alias in _ks_gene_id_aliases(real_id):
            previous = alias_to_real.get(alias)
            if previous is None:
                alias_to_real[alias] = real_id
            elif previous != real_id:
                ambiguous_aliases.add(alias)
    for alias in ambiguous_aliases:
        alias_to_real.pop(alias, None)
    return alias_to_real


def _resolve_ks_sequence_id(token, alias_map):
    for alias in _ks_gene_id_aliases(token):
        real_id = alias_map.get(alias)
        if real_id:
            return real_id
    return None


def _collect_wgdi_cleaned_pair_ids(pairs_path):
    pair_ids = set()
    if not os.path.isfile(pairs_path):
        return pair_ids
    with open(pairs_path, 'r', encoding='utf-8', errors='ignore') as pairs_handle:
        for line in pairs_handle:
            parts = line.strip().split()
            if len(parts) >= 2:
                pair_ids.add(parts[0])
                pair_ids.add(parts[1])
    return pair_ids


def _read_fasta_records_by_id(fasta_path, keep_ids=None):
    """Read FASTA records and keep one record per first-token ID.

    Bio.SeqIO.to_dict aborts when a FASTA contains duplicate IDs.  Some
    ancestral FASTA files contain repeated gene IDs, so before WGDI -ks we
    rewrite the combined CDS/PEP FASTA files to a unique-ID version.  When a
    duplicate ID is encountered, the longest sequence is kept because WGDI -ks
    only needs a single representative CDS/PEP sequence per collinear gene.
    """
    keep_ids = set(keep_ids or [])
    restrict_ids = bool(keep_ids)
    records = {}
    duplicate_ids = set()
    total_records = 0
    skipped_records = 0
    current_header = None
    current_sequence = []

    def flush_record():
        nonlocal current_header, current_sequence, total_records, skipped_records
        if current_header is None:
            return
        total_records += 1
        record_id = current_header[1:].strip().split()[0] if current_header[1:].strip().split() else ''
        sequence = ''.join(current_sequence).replace(' ', '').replace('\t', '')
        if not record_id or (restrict_ids and record_id not in keep_ids):
            skipped_records += 1
            return
        previous = records.get(record_id)
        if previous is not None:
            duplicate_ids.add(record_id)
            # Keep the longest available sequence.  If lengths tie, retain the
            # first one to keep behavior deterministic.
            if len(sequence) > len(previous[1]):
                records[record_id] = (current_header, sequence)
        else:
            records[record_id] = (current_header, sequence)

    with open(fasta_path, 'r', encoding='utf-8', errors='ignore') as fasta_handle:
        for raw_line in fasta_handle:
            line = raw_line.rstrip('\n\r')
            if line.startswith('>'):
                flush_record()
                current_header = line
                current_sequence = []
            else:
                current_sequence.append(line.strip())
        flush_record()

    return records, {
        'file': os.path.basename(fasta_path),
        'total_records': total_records,
        'unique_records': len(records),
        'duplicate_id_count': len(duplicate_ids),
        'duplicate_id_examples': sorted(duplicate_ids)[:20],
        'skipped_records': skipped_records,
        'restricted_to_pair_ids': restrict_ids,
    }


def _write_unique_fasta_records(fasta_path, records, pair_ids=None):
    pair_ids = list(pair_ids or [])
    if pair_ids:
        ordered_ids = [record_id for record_id in pair_ids if record_id in records]
    else:
        ordered_ids = list(records.keys())

    with open(fasta_path, 'w', encoding='utf-8') as output_handle:
        for record_id in ordered_ids:
            header, sequence = records[record_id]
            output_handle.write(header + '\n')
            for start in range(0, len(sequence), 80):
                output_handle.write(sequence[start:start + 80] + '\n')
    return len(ordered_ids)


def cleanup_wgdi_ks_fasta_files(work_dir, pairs_file):
    """Make cds.fasta and pep.fasta safe for WGDI -ks.

    WGDI -ks internally uses ``SeqIO.to_dict`` on the full PEP/CDS FASTA files,
    so a duplicated FASTA header anywhere in the file can crash the job even if
    that duplicated gene is not used by the collinearity pairs.  This function
    rewrites the FASTA files to contain only IDs used in the cleaned pair file
    and only one sequence per ID.
    """
    pairs_path = os.path.join(work_dir, pairs_file)
    pair_ids = _collect_wgdi_cleaned_pair_ids(pairs_path)
    if not pair_ids:
        raise RuntimeError('No gene IDs were found in the cleaned collinearity pair file.')

    ordered_pair_ids = []
    with open(pairs_path, 'r', encoding='utf-8', errors='ignore') as pairs_handle:
        for line in pairs_handle:
            parts = line.strip().split()
            if len(parts) >= 2:
                for gene_id in parts[:2]:
                    if gene_id not in ordered_pair_ids:
                        ordered_pair_ids.append(gene_id)

    summary = {'pair_id_count': len(pair_ids), 'files': {}}
    for fasta_name in ('pep.fasta', 'cds.fasta'):
        fasta_path = os.path.join(work_dir, fasta_name)
        backup_path = os.path.join(work_dir, fasta_name + '.raw_before_ks_cleanup')
        if os.path.isfile(fasta_path) and not os.path.isfile(backup_path):
            shutil.copyfile(fasta_path, backup_path)
        records, file_summary = _read_fasta_records_by_id(fasta_path, keep_ids=pair_ids)
        missing_ids = sorted(pair_ids - set(records.keys()))
        file_summary['missing_pair_id_count'] = len(missing_ids)
        file_summary['missing_pair_id_examples'] = missing_ids[:20]
        if missing_ids:
            raise RuntimeError(
                f'{fasta_name} is missing {len(missing_ids)} gene IDs required by colinearity.cleaned.txt. '
                f'Examples: {", ".join(missing_ids[:10])}'
            )
        written_count = _write_unique_fasta_records(fasta_path, records, ordered_pair_ids)
        file_summary['written_records'] = written_count
        summary['files'][fasta_name] = file_summary

    with open(os.path.join(work_dir, 'ks_fasta.cleanup.log'), 'w', encoding='utf-8') as report_file:
        report_file.write(json.dumps(summary, ensure_ascii=False, indent=2))
        report_file.write('\n')
    return summary


def _extract_valid_pair_from_collinearity_parts(parts, alias_map):
    """Extract a valid two-gene pair from a WGDI/MCScan-like line.

    WGDI -ks can read a simple two-column tab-separated gene-pair file, so
    we do not need to preserve the original collinearity line.  The old code
    assumed gene IDs were always in columns 0 and 2; however different WGDI
    outputs can contain block/order/index columns before the IDs.  This helper
    first tries the common positions, then falls back to finding the first two
    tokens that resolve to sequence IDs present in both CDS and PEP files.
    """
    common_positions = ((0, 2), (0, 1), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4))
    for left_index, right_index in common_positions:
        if len(parts) <= max(left_index, right_index):
            continue
        left = _resolve_ks_sequence_id(parts[left_index], alias_map)
        right = _resolve_ks_sequence_id(parts[right_index], alias_map)
        if left and right and left != right:
            return left, right

    resolved = []
    for part in parts:
        gene_id = _resolve_ks_sequence_id(part, alias_map)
        if gene_id and gene_id not in resolved:
            resolved.append(gene_id)
        if len(resolved) >= 2:
            return resolved[0], resolved[1]
    return None


def clean_wgdi_ks_pairs_file(place):
    work_dir = os.path.join(path_get, 'file_keep', place)
    pairs_file = os.path.join(work_dir, 'colinearity.txt')
    cleaned_file = os.path.join(work_dir, 'colinearity.cleaned.txt')
    cleanup_report = os.path.join(work_dir, 'colinearity.cleanup.log')
    cds_ids = get_fasta_record_ids(os.path.join(work_dir, 'cds.fasta'))
    pep_ids = get_fasta_record_ids(os.path.join(work_dir, 'pep.fasta'))
    valid_sequence_ids = cds_ids & pep_ids
    alias_map = _build_ks_alias_map(valid_sequence_ids)

    kept_pairs = 0
    skipped_lines = 0
    missing_sequence_pairs = 0
    duplicate_pairs = 0
    cleaned_lines = []
    seen_pairs = set()
    missing_examples = []
    skipped_examples = []

    if not valid_sequence_ids:
        with open(cleanup_report, 'w', encoding='utf-8') as report_file:
            report_file.write('valid_pairs=0\n')
            report_file.write(f'cds_id_count={len(cds_ids)}\n')
            report_file.write(f'pep_id_count={len(pep_ids)}\n')
            report_file.write('shared_cds_pep_id_count=0\n')
        raise RuntimeError(
            'No shared FASTA IDs were found between cds.fasta and pep.fasta. '
            'WGDI -ks requires the same gene IDs in both CDS and PEP files.'
        )

    with open(pairs_file, 'r', encoding='utf-8', errors='ignore') as input_file:
        for line in input_file:
            stripped = line.strip()
            if not stripped:
                continue

            if (
                stripped.startswith('+++++++++++++++++')
                or stripped.startswith('the ')
                or stripped.startswith('>LOCALE')
                or stripped.startswith('#')
                or stripped.startswith('##')
                or stripped.startswith('###')
            ):
                continue

            parts = stripped.split()
            if len(parts) < 2:
                skipped_lines += 1
                if len(skipped_examples) < 10:
                    skipped_examples.append(stripped)
                continue

            pair = _extract_valid_pair_from_collinearity_parts(parts, alias_map)
            if not pair:
                missing_sequence_pairs += 1
                if len(missing_examples) < 20:
                    missing_examples.append(stripped)
                continue

            pair_key = tuple(pair)
            if pair_key in seen_pairs:
                duplicate_pairs += 1
                continue
            seen_pairs.add(pair_key)
            cleaned_lines.append(f'{pair[0]}\t{pair[1]}\n')
            kept_pairs += 1

    with open(cleanup_report, 'w', encoding='utf-8') as report_file:
        report_file.write(f'valid_pairs={kept_pairs}\n')
        report_file.write(f'skipped_non_pair_lines={skipped_lines}\n')
        report_file.write(f'skipped_missing_sequence_pairs={missing_sequence_pairs}\n')
        report_file.write(f'skipped_duplicate_pairs={duplicate_pairs}\n')
        report_file.write(f'cds_id_count={len(cds_ids)}\n')
        report_file.write(f'pep_id_count={len(pep_ids)}\n')
        report_file.write(f'shared_cds_pep_id_count={len(valid_sequence_ids)}\n')
        if missing_examples:
            report_file.write('missing_or_unparsed_examples:\n')
            for example in missing_examples:
                report_file.write(example + '\n')
        if skipped_examples:
            report_file.write('skipped_examples:\n')
            for example in skipped_examples:
                report_file.write(example + '\n')

    if kept_pairs == 0:
        raise RuntimeError(
            'Colinearity file contains no valid gene pairs after cleanup. '
            'Most likely the collinearity gene IDs do not exactly match the IDs shared by cds.fasta and pep.fasta, '
            'or the collinearity line format is different from the previous parser. '
            'See colinearity.cleanup.log for examples and ID counts.'
        )

    with open(cleaned_file, 'w', encoding='utf-8') as output_file:
        output_file.writelines(cleaned_lines)

    return os.path.basename(cleaned_file)


def wgdikaks_run_tools(place):
    work_dir = os.path.join(path_get, 'file_keep', place)
    pairs_file = clean_wgdi_ks_pairs_file(place)
    cleanup_wgdi_ks_fasta_files(work_dir, pairs_file)
    write_txt = (str("[ks]") + "\n" + str("cds_file = cds.fasta") + "\n" + str("pep_file = pep.fasta") + "\n" +
                 str("align_software = mafft") + "\n" + str(f"pairs_file = {pairs_file}") + "\n" +
                 str("ks_file = ks_result.txt") + "\n"
                 )
    text_create('ath', str(write_txt), place)

    run_wgdi_subcommand(place, '-ks')

def zu_blast_dotplot_run_tools(place, shu_len_name, heng_len_name):
    work_dir = os.path.join(path_get, 'file_keep', place)
    source_candidates = [
        os.path.join(path_get, 'file_keep', 'programs', 'run_mc', '6.corr_dotplot_spc_last.py'),
        os.path.join(path_get, 'file_keep', 'programs', 'corr_dotplot_spc_last.py'),
        os.path.join(path_get, 'tools', 'offline_views', 'Paleo_gene_identifer', '6.corr_dotplot_spc_last.py'),
    ]

    script_source = next((item for item in source_candidates if os.path.exists(item)), None)
    if script_source is None:
        raise FileNotFoundError("corr_dotplot_spc_last.py not found.")

    script_target = os.path.join(work_dir, 'corr_dotplot_spc_last.py')
    shutil.copy(script_source, script_target)

    python_executable = get_real_python_executable()
    subprocess.run(
        [python_executable, 'corr_dotplot_spc_last.py', shu_len_name, heng_len_name],
        cwd=work_dir,
        check=True,
    )


def zu_block_dotplot_run_tools(place, shu_len_name, heng_len_name, block_num):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        cp ../programs/dotplot_block.2400.pd.py .
        python3 dotplot_block.2400.pd.py {shu_len_name} {heng_len_name} {block_num}
    """
    subprocess.run(cmd, shell=True, check=True)


def zu_ks_dotplot_run_tools(place, shu_len_name, heng_len_name):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        cp ../programs/ks_dot/* .
        python3 run_ks_dot.py {shu_len_name} {heng_len_name}
    """
    subprocess.run(cmd, shell=True, check=True)


# WGDI ---blast_dotplot---
def wgdi_dotplot_run_tools(place, evalue, score, heng_species, shu_species, patten):
    global path_get

    write_txt = (str("[dotplot]") + "\n" + str(f"blast = diamond.fasta") + "\n" +
                 str("gff1 =  11.gff") + "\n" + str("gff2 =  22.gff") + "\n" + str("lens1 = 11.len") + "\n" +
                 str("lens2 = 22.len") + "\n" + str(f"genome1_name =  {heng_species}") + "\n" + str(
                f"genome2_name =  {shu_species}") + "\n" +
                 str("multiple  = 1") + "\n" + str(f"score = {score}") + "\n" + str(f"evalue = {evalue}") + "\n" +
                 str("repeat_number = 10") + "\n" + str("position = order") + "\n" + str(
                "blast_reverse = false") + "\n" +
                 str("ancestor_left = none") + "\n" + str("ancestor_top = none") + "\n" + str(
                "markersize = 0.5") + "\n" +
                 str("figsize = 10,10") + "\n" + str(f"savefig = result.{patten}") + "\n" + "\n"
                 )
    text_create('ath', str(write_txt), place)

    run_wgdi_subcommand(place, '-d')


# WGDI ---绘制kaks点图---
def wgdikaks_dot_run_tools(place, heng_species, shu_species):
    write_txt = (str("[blockks]") + "\n" + str(f"lens1 = 11.len") + "\n" +
                 str("lens2 = 22.len") + "\n" + str(f"genome1_name =  {heng_species}") + "\n" +
                 str(f"genome2_name =  {shu_species}") + "\n" + str("blockinfo =  blockinfo.csv") + "\n" +
                 str("pvalue = 0.05") + "\n" + str("tandem = true") + "\n" +
                 str("tandem_length = 200") + "\n" + str("markersize = 1") + "\n" + str("area = 0,3") + "\n" +
                 str("block_length =  5") + "\n" + str("figsize = 8,8") + "\n" +
                 str("savefig = ks.dotplot.pdf") + "\n" + "\n")
    text_create('ath', str(write_txt), place)

    run_wgdi_subcommand(place, '-bk')


# zu_correspondence_mc_run_tools
def zu_correspondence_mc_run_tools(place, shu_name, heng_name):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        cp ../programs/run_mc/* .
        sed -i 's/\r$//' run_all_1_6.sh
        sh run_all_1_6.sh {shu_name} {heng_name}
    """
    subprocess.run(cmd, shell=True, check=True)


def zu_retention_run_tools(place):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        cp ../programs/baoliu.py .
        mkdir output
        python3 baoliu.py
    """
    subprocess.run(cmd, shell=True, check=True)


def zu_loss_run_tools(place):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        cp ../programs/lost.py .
        mkdir output
        python3 lost.py
    """
    subprocess.run(cmd, shell=True, check=True)


# zu_pindex_run
def zu_pindex_run_tools(place, sliding_window, buchang, sigema_start, sigema_end):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        cp ../programs/p_index.py .
        mkdir output
        python3 p_index.py {sliding_window} {buchang} {sigema_start} {sigema_end} > pindex_result.txt
    """
    subprocess.run(cmd, shell=True, check=True)


# WGDI --- blockinfo_run_tools
def wgdi_blockinfo_run_tools(place, evalue, score, repeat_number, heng_species,shu_species):
    global path_get

    write_txt = (
        "[blockinfo]\n"
        "blast = blast.txt\n"
        "collinearity = block.txt\n"
        "ks = ks.txt\n"
        "gff1 = 11.gff\n"
        "gff2 = 22.gff\n"
        "lens1 = 11.len\n"
        "lens2 = 22.len\n"
        f"evalue = {evalue}\n"
        f"score = {score}\n"
        f"repeat_number = {repeat_number}\n"
        "position = order\n"
        "ks_col = ks_NG86\n"
        f"savefile = {heng_species}_{shu_species}_block_information.csv\n"
    )
    text_create('ath', str(write_txt), place)
    run_wgdi_subcommand(place, '-bi', timeout_seconds=1800)


# WGDI --- wgdi_correspondence_run
def wgdi_correspondence_run_tools(place, tandem_length, pvalue, block_length):
    write_txt = (str("[correspondence]") + "\n" + str("blockinfo = block_information.csv") + "\n" + str("lens1 = 11.len") + "\n" + str("lens2 = 22.len") + "\n" + str(f"tandem_length = {tandem_length}") + "\n" + str(f"pvalue = {pvalue}") + "\n" + str(f"block_length = {block_length}") + "\n" + str("multiple  = 1") + "\n" + str("position = end") + "\n" + str("tandem = true") + "\n" + str(f"homo = 0,1") + "\n" + str("savefile = Correspondence.csv"))
    text_create('ath', str(write_txt), place)
    run_wgdi_subcommand(place, '-c', timeout_seconds=7200)


# codonw_run
def codonw_run_tools(place, file_name):
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        codonw 1.fasta -all_indices -nomenu {file_name}.out {file_name}.blk
    """
    os.system(cmd)

# cpgfinder_run
def cpgfinder_run_tools(place, island, cg_percent, gc_ratio, myFile_name):
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        cpgfinder -f {myFile_name} -l {island} -p {cg_percent} -r {gc_ratio} > cpgfinder_result.txt
    """
    os.system(cmd)


# meme
def meme_run_tools(place, patten, motif, motif_num, minw, maxw):
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        meme 1.fasta -{patten} -oc . -mod {motif} -nmotifs {motif_num} -minw {minw} -maxw {maxw}
    """
    subprocess.run(cmd, shell=True, check=True)


# hmmer
def hmmer_run_tools(place, e_value):
    cmd = f"""
        cd {path_get}/file_keep/{place}
        hmmbuild db_model.hmm hmm_model.fasta
        hmmsearch -o result.out --noali -E {e_value} db_model.hmm hmm_fa.fasta
    """
    os.system(cmd)


# pfam
def pfam_run_tools(place, structure):
    # pfam_scan.pl -fasta 1.fasta -dir ~/../../../../www/tools/PfamScan/pfamdata -outfile pfam.txt
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        pfam_scan.pl -fasta 1.fasta -dir ~/../../../../www/tools/PfamScan/pfamdata -outfile pfam.txt
    """
    os.system(cmd)

    deal = ('#', ' ', '\n')
    with open(f'{path_get}/file_keep/{place}/pfam.txt', 'r') as file, open(f'{path_get}/file_keep/{place}/pfam_new.txt', 'w') as pfam_new:
        structure_list = set(structure.split(';'))
        pfam_new.writelines(line for line in file if not line.startswith(deal) and line.split()[6] in structure_list)


# sequence_aligment
def sequence_aligment_run_tools(place, patten):
    if patten == "clustalw2":
        cmd = f"""
            source /etc/profile
            cd {path_get}/file_keep/{place}
            clustalw2 1.fasta
        """
        os.system(cmd)
    elif patten == "muscle":
        cmd = f"""
            source /etc/profile
            cd {path_get}/file_keep/{place}
            muscle -in 1.fasta -clwout 1.aln
        """
        os.system(cmd)
    elif patten == "mafft":
        cmd = f"""
            source /etc/profile
            cd {path_get}/file_keep/{place}
            mafft --auto 1.fasta > mafft.fasta
        """
        os.system(cmd)


# fasttree
def fasttree_run_tools(place, patten):
    if patten == "JTT+CAT":
        cmd = f"""
            source /etc/profile
            cd {path_get}/file_keep/{place}
            FastTree 1.phy > 1.nwk
        """
        os.system(cmd)
    else:
        cmd = f"""
            source /etc/profile
             cd {path_get}/file_keep/{place}
            FastTree -gtr -nt  1.phy > 1.nwk
        """
        os.system(cmd)


# iqtree
def iqtree_run_tools(place, patten, bs_num):
    from tools.command_safety import iqtree
    return iqtree(place, patten, bs_num)


# sequence_screening_clas
class sequence_run2(object):
    def __init__(self, place):
        self.id_list = []
        self.place = place

    def new_prot(self):
        new_prot = open(f'{path_get}/file_keep/{self.place}/new_pro.txt', 'w')
        for line in SeqIO.parse(f'{path_get}/file_keep/{self.place}/protein.fasta', 'fasta'):
            if line.id in self.id_list:
                new_prot.write('>' + str(line.id) + '\n' + str(line.seq) + '\n')

    def new_cds(self):
        new_cds = open(f'{path_get}/file_keep/{self.place}/new_cds.txt', 'w')
        for line in SeqIO.parse(f'{path_get}/file_keep/{self.place}/gene.fasta', 'fasta'):
            if line.id in self.id_list:
                new_cds.write('>' + str(line.id) + '\n' + str(line.seq) + '\n')

    def new_gff(self):
        new_gff = open(f'{path_get}/file_keep/{self.place}/new_gff.txt', 'w')
        gff_file = open(f'{path_get}/file_keep/{self.place}/gff.fasta', 'r')
        for line in gff_file:
            gff_id = line.split()[1]
            if gff_id in self.id_list:
                new_gff.write(line)

    def main(self):
        id_file = open(f'{path_get}/file_keep/{self.place}/id.fasta', 'r')
        for line in id_file.readlines():
            self.id_list.append(line.split()[0])

        self.new_prot()
        self.new_cds()
        self.new_gff()


# sequence_screening
def sequence_run(place):
    run = sequence_run2(place)
    run.main()


# formatTofasta
def format_fasta_run(place, file_name, patten, patten_end, file_last):
    SeqIO.convert(f"{path_get}/file_keep/{place}/{file_name}.{file_last}", f"{patten}",
                  f"{path_get}/file_keep/{place}/{file_name}.{patten_end}", f"{patten_end}")


# find_replace_run
def find_replace_run_tools(place, old_name, new_name):
    from tools.command_safety import find_replace
    return find_replace(place, old_name, new_name)

# quchong_run
def quchong_run(place):
    id_list = []
    new_file = open(f'{path_get}/file_keep/{place}/new.fasta', 'w')
    for line in SeqIO.parse(f'{path_get}/file_keep/{place}/1.fasta', 'fasta'):
        if line.id not in id_list:
            id_list.append(line.id)
            new_file.write(">" + str(line.id) + "\n" + str(line.seq) + "\n")
    new_file.close()


# extr_row_run
def extr_row_run(place, row_num, row_name, row_last):
    from tools.command_safety import extract_columns
    return extract_columns(place, row_num, row_name, row_last)


# file_merge_run
def file_merge_run_tools(place):
    cmd = f"""
        cd '{path_get}/file_keep/{place}'
        cat orthomcl/* >> result.txt
    """
    subprocess.run(cmd, shell=True, check=True)


# interproscan_ 跑
def interproscan_run_tools(place):
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        interproscan.sh -i result.fasta -b . -goterms -iprlookup -pa -dp -f tsv -cpu 8
    """
    os.system(cmd)


def deal_pep_star(pep):
    pep_name = os.path.basename(pep)
    new_pep_path = os.path.join("output_pep", pep_name)
    with open(pep, "r") as input_file, open(new_pep_path, "w") as output_file:
        translation_table = str.maketrans("", "", "*.")
        for line in SeqIO.parse(input_file, "fasta"):
            line.seq = str(line.seq).translate(translation_table)
            output_file.write(f">{line.id}\n{line.seq}\n")


# deal_star_run_tools
def deal_star_run_tools(place):
    cmd = f"""
        cd '{path_get}/file_keep/{place}'
    """
    subprocess.run(cmd, shell=True, check=True)

    output_pep = "output_pep"
    shutil.rmtree(output_pep, ignore_errors=True)
    os.makedirs(output_pep)

    pep_files = glob.glob("orthomcl/*")
    with ProcessPoolExecutor(max_workers=2) as executor:
        executor.map(deal_pep_star, pep_files)


def prune_tree_by_taxa(input_tree_file, taxa_list_file, output_tree_file):
    with open(input_tree_file, 'r') as tree_file:
        tree_content = "".join(tree_file.readlines()).strip()
    tree = Tree(tree_content)
    with open(taxa_list_file, "r") as taxa_file:
        subtree_taxa = [line.split()[0] for line in taxa_file]
    intersection_nodes = set(subtree_taxa) & set(tree.get_leaf_names())
    tree.prune(intersection_nodes, preserve_branch_length=True)
    tree.write(outfile=output_tree_file, format=1)


# subtree_extractor_run_tools
def subtree_extractor_run_tools(place):
    cmd = f"cd {path_get}/file_keep/{place}"
    subprocess.run(cmd, shell=True, check=True)

    input_tree_file = "ty.newick"  # 改 - 输入newick格式树文件
    taxa_list_file = "species.txt"  # 改 - 输入物种列表文件
    output_tree_file = "result_subtree.newick"  # 改 - 输出结果文件

    prune_tree_by_taxa(input_tree_file, taxa_list_file, output_tree_file)


# 1.run iTAK
def run_pfam(input_file, CPU):
    file_name = os.path.basename(input_file).split(".")[0]
    cmd = ["iTAK.pl", input_file]
    print("Running command: ", " ".join(cmd))
    subprocess.run(cmd)

# 2.结果移动到output文件夹
def move_files():
    os.makedirs("output", exist_ok=True)
    input_files = glob.glob("orthomcl/*")
    for file in input_files:
        if os.path.isdir(file):
            shutil.move(file, os.path.join("output", os.path.basename(file)))

def iTAK_run_tools(place):
    cmd = f"cd {path_get}/file_keep/{place}"
    subprocess.run(cmd, shell=True, check=True)

    pep_file = glob.glob("orthomcl/*.pep")  # （可改） - 文件的路径和文件后缀
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:  # 改 - 线程池最大线程数
        for file in pep_file:
            executor.submit(run_pfam, file, 8)  # 改 - 运行单个文件所占的CPU
    move_files()


class CountBlock:
    def __init__(self, path):
        self.path = path
        self.flag = 0
        self.genenum_dit1 = {i: [] for i in [4, 10, 20, 50]}
        self.genenum_dit2 = {i: [] for i in [4, 10, 20, 50]}
        self.format_ = '{:^15}{:^15}{:^15}{:^15}{:^15}{:^25}{:^15}{:^15}'
        self.format1 = '{:^15}'
        print(self.format_.format('name', 'BL>4', 'BL>10', 'BL>20', 'BL>50', 'ACGP', 'LDB',
                                  'LDB on chromosomes'))
        self.writer = csv.writer(open('block.all.count.csv', 'w', newline=''))
        self.sf2_ = open('block.all.count.gene_num.csv', 'w')
        self.writer.writerow(['name', 'BL>4', 'BL>10', 'BL>20', 'BL>50', 'ACGP', 'LDB',
                                 'LDB on chromosomes'])
        self.sf2_.write(','.join(['name', 'BL>4', 'BL>10', 'BL>20', 'BL>50'])+'\n')

    def count_gene(self, key, blocks):
        gene1 = []
        gene2 = []
        if not self.flag:
            for li in blocks:
                ls = re.split('\\s', li)
                gene1.append(ls[0])
                gene1.append(ls[2])
            self.genenum_dit1[key].extend(gene1)

        else:
            for li in blocks:
                ls = re.split('\\s', li)
                gene1.append(ls[0])
                gene2.append(ls[2])
            self.genenum_dit1[key].extend(gene1)
            self.genenum_dit2[key].extend(gene2)

    @staticmethod
    def collection():
        lines = []
        files = glob.glob('*.block.count.txt')
        sf = open('block.all.count.txt', 'w')
        for f_n in files:
            for li in open(f_n, 'r'):
                if li not in lines:
                    lines.append(li)
                    sf.write(li)

    @staticmethod
    def remove_tandem(blocks):
        num = 0
        for i in range(len(blocks)):
            block = []
            for li in blocks[i]:
                if 'overlap' in li or '>LOCALE' in li \
                        or 'the' in li or 'self' in li \
                        or '>' in li:
                    continue
                pairs = re.split('\\s', li)
                na1 = re.split('[g|B|G]', pairs[0])[0]
                na2 = re.split('[g|B|G]', pairs[2])[0]
                block.append(li)
            if block:
                num += 1
            blocks[i] = block
        print('block num:%d' % num)
        return blocks

    def get_block(self, path):
        da = open(path, 'r')
        blocks = []
        block = []
        for li in da:
            li = li.strip()
            if 'the' in li:
                block.append(li)
            elif '>' in li:
                block.append(li)
                blocks.append(block)
                block = []
            elif 'overlap' in li or 'self' in li or \
                    'LOCALE' in li or 'MAXIMUM' in li or\
                    'p-value' in li:
                continue
            elif li:
                block.append(li)

        return blocks

    def colinearscan_(self, name, path):
        nas = name.split('_')
        if nas[0] != nas[1]:
            self.flag = 1
        max_block_len = 0
        max_block_chr = ''
        a, a_block_num, b, b_block_num = 0, 0, 0, 0
        c, c_block_num, d, d_block_num = 0, 0, 0, 0
        blocks = self.get_block(path)
        blocks = self.remove_tandem(blocks)
        for block in blocks:
            if 10 > len(block) >= 4:
                a += 1
                a_block_num += len(block)
                self.count_gene(4, block)
            if 20 > len(block) >= 10:
                b += 1
                b_block_num += len(block)
                self.count_gene(10, block)
            if 50 > len(block) >= 20:
                c += 1
                c_block_num += len(block)
                self.count_gene(20, block)
            if len(block) >= 50:
                d += 1
                d_block_num += len(block)
                self.count_gene(50, block)
            if len(block) > max_block_len:
                ids = re.split('\\s', block[0])
                max_block_len = len(block)
                max_block_chr = ids[0][0:5]+'-'+ids[2][0:5]

        ACGPa = round(a_block_num/a, 2)
        ACGPb = round(b_block_num/b, 2)
        if c == 0:
            ACGPc = 0
        else:
            ACGPc = round(c_block_num/c, 2)
        if d == 0:
            ACGPd = 0
        else:
            ACGPd = round(d_block_num/d, 2)

        # save file
        result_int = [name, f'{a_block_num}/{a}', f'{b_block_num}/{b}',
                      f'{c_block_num}/{c}', f'{d_block_num}/{d}',
                      f'{ACGPa},{ACGPb},{ACGPc},{ACGPd}', max_block_len, max_block_chr]
        result_str = [str(i) for i in result_int]
        self.writer.writerow(result_str)
        print(self.format_.format(name, f'{a_block_num}/{a}', f'{b_block_num}/{b}',
              f'{c_block_num}/{c}', f'{d_block_num}/{d}', f'{ACGPa},{ACGPb},{ACGPc},{ACGPd}',
                                  max_block_len, max_block_chr))
        print(self.format1.format(name), end='')

        self.sf2_.write(name)
        if not self.flag:
            for k, v in self.genenum_dit1.items():
                print(self.format1.format(len(list(set(v)))), end='')
                self.sf2_.write(','+str(len(list(set(v)))))
            self.sf2_.write('\n')
        else:
            for k in [4, 10, 20, 50]:
                s = f'{len(list(set(self.genenum_dit1[k])))} vs {len(list(set(self.genenum_dit2[k])))}'
                self.sf2_.write(','+s)
                print(self.format1.format(s), end='')
            self.sf2_.write('\n')
        print()

    def run(self):
        fs = glob.glob(self.path)
        for fn in fs:
            self.flag = 0
            self.genenum_dit1 = {i: [] for i in [4, 10, 20, 50]}
            self.genenum_dit2 = {i: [] for i in [4, 10, 20, 50]}
            name = os.path.basename(fn).split('.')[0]
            self.colinearscan_(name, fn)


def block_number_count_run_tools(place):
    # 文件格式A_B.block.*.txt  A_B与文件中物种的列对应
    cmd = f"cd {path_get}/file_keep/{place}"
    subprocess.run(cmd, shell=True, check=True)
    path = '*.block.rr.txt'
    r = CountBlock(path)
    r.run()


# 生成共线性列表 - 两套
def collinearity_generator_run_two(file_list, pvu_file, output_file, species_name):
    data = pd.DataFrame()
    for file in file_list:
        df = pd.read_csv(file, sep="\t", header=None)
        data = pd.concat([data, df], axis=1)
    data = data.loc[:, (data != ".").any(axis=0)]
    data = data.loc[:, ~(data.applymap(type) == int).all(axis=0)]
    data = data.iloc[:,[0] + [i for i in range(1, len(data.columns)) if not data.iloc[:,i].str.contains(species_name).any()]]
    data_dict = data.set_index(0).T.to_dict('list')
    pvu_df = pd.read_csv(pvu_file, sep="\t", header=None)
    data = pd.concat([data, pvu_df[1]], axis=1)
    num_elements = len(data.columns) - 2
    data_dict_col = data.iloc[:, -1].apply(lambda x: '\t'.join(data_dict[x]) if x in data_dict else x)
    data_dict_col = data_dict_col.str.split('\t', expand=True)
    data_dict_col = data_dict_col.fillna(".")
    data = pd.concat([data, data_dict_col], axis=1)
    data.to_csv(output_file, index=False, header=False, sep="\t")

# 生成共线性列表 - 三套
def collinearity_generator_run_three(file_list, pvu_file, output_file, species_name):
    data = pd.DataFrame()
    for file in file_list:
        df = pd.read_csv(file, sep="\t", header=None)
        data = pd.concat([data, df], axis=1)
    data = data.loc[:, (data != ".").any(axis=0)]
    data = data.loc[:, (data != " ").any(axis=0)]
    data = data.loc[:, ~(data.applymap(type) == int).all(axis=0)]
    data = data.iloc[:,[0] + [i for i in range(1, len(data.columns)) if not data.iloc[:,i].str.contains(species_name).any()]]
    data_dict = data.set_index(0).T.to_dict('list')
    # Vvi 第二套
    pvu_df = pd.read_csv(pvu_file, sep="\t", header=None)
    data = pd.concat([data, pvu_df[1]], axis=1)
    num_elements = len(data.columns) - 2
    data_dict_col = data.iloc[:, -1].apply(lambda x: '\t'.join(data_dict[x]) if x in data_dict else x)
    data_dict_col = data_dict_col.str.split('\t', expand=True)
    data_dict_col = data_dict_col.fillna(".")
    data = pd.concat([data, data_dict_col], axis=1)
    # Vvi 第三套
    data = pd.concat([data, pvu_df[2]], axis=1)
    data_dict_col = data.iloc[:, -1].apply(lambda x: '\t'.join(data_dict[x]) if x in data_dict else x)
    data_dict_col = data_dict_col.str.split('\t', expand=True)
    data_dict_col = data_dict_col.fillna(".")
    data = pd.concat([data, data_dict_col], axis=1)
    data.to_csv(output_file, index=False, header=False, sep="\t")

# collinearity_generator_run_tools
def collinearity_generator_run_tools(place, patten, reference_file, species_name):
    # 1. 定义工作目录的绝对路径
    # 指向: path_get/file_keep/随机字符文件夹/
    work_dir = os.path.join(path_get, 'file_keep', place)
    
    # 2. 获取上传文件的绝对路径
    # keep_files 把文件存到了 work_dir 下的 orthomcl 文件夹里
    # 使用 glob 在绝对路径下查找
    mc_files_pattern = os.path.join(work_dir, "orthomcl", "*.txt")
    target_files = glob.glob(mc_files_pattern)

    # 安全检查：如果没找到文件，打印错误日志（防止静默崩溃）
    if not target_files:
        print(f"Error: No files found in {mc_files_pattern}")
        # 这里你可以选择 raise 一个错误，或者让它继续（可能会报错）

    # 3. 定位参考文件 (Reference File)
    # 假设 'input_file' 文件夹位于项目根目录 (path_get) 下
    # 如果你的参考文件存放在其他位置，请修改这里的路径
    ref_file_path = os.path.join(path_get, 'input_file', reference_file)
    
    # 检查参考文件是否存在
    if not os.path.exists(ref_file_path):
        print(f"Error: Reference file not found at {ref_file_path}")

    # 4. 定义输出文件的绝对路径
    # 结果将生成在 work_dir 下
    output_file_path = os.path.join(work_dir, "output.txt")

    # 5. 调用处理逻辑，传入绝对路径
    # 注意：这里传入的是完整路径，所以你的 _two 和 _three 函数不需要改动逻辑
    # 只要 pd.read_csv 能读到这个路径即可
    if patten == "two":
        collinearity_generator_run_two(
            target_files, 
            ref_file_path, 
            output_file_path, 
            species_name
        )
    else:
        collinearity_generator_run_three(
            target_files, 
            ref_file_path, 
            output_file_path, 
            species_name
        )


# 构建列表系统发育树
class ListTree:
    def __init__(self, input_pep_files, vvi_file, additional_parameter=False):
        self.input_pep_files = input_pep_files
        self.vvi_file = vvi_file
        self.additional_parameter = additional_parameter

    def pep_files_ids(self):
        pep_gene_ids = {}
        for file in self.input_pep_files:
            file_name = os.path.basename(file).split(".")[0]
            pep_gene_ids[file_name] = {record.id: str(record.seq).replace("*", "").replace(".", "") for record in
                                       SeqIO.parse(file, "fasta")}
        return pep_gene_ids

    def write_tree_file(self, sp_geneid_dict):
        shutil.rmtree("output", ignore_errors=True)
        os.makedirs("output", exist_ok=True)

        with open(self.vvi_file, 'r') as mc_file:
            for line in mc_file:
                new_line = line.split()
                vvi_name = new_line[0]
                with open(f'output/{vvi_name}.txt', 'w') as new_file:
                    for hh_line in new_line:
                        if hh_line != ".":
                            gene_id = ''.join(filter(str.isalpha, hh_line.split("g")[0]))
                            new_file.write(">" + hh_line + '\n' + str(sp_geneid_dict[gene_id][hh_line]) + '\n')

    def draw_tree(self, name_file):
        file_name = os.path.basename(name_file).split(".")[0]
        tree = Phylo.read(f"{name_file}", "newick")
        Phylo.draw_ascii(tree)
        outgroup_clade = next((clade for clade in tree.find_clades() if clade.name == file_name), None)
        if outgroup_clade is None:
            raise ValueError(f"target '{file_name}' is not in this tree")

        if self.additional_parameter:
            tree.root_with_outgroup(outgroup_clade)  # 以外群进化枝的最近共同祖先为根节点

        Phylo.draw(tree)  # 绘制进化树
        pylab.show()  # 显示进化树
        pylab.savefig(f"{name_file}.png")  # （可改） - 保存进化树为 png 格式
        # pylab.savefig(f"{name_file}.pdf")  #（可改） - 保存进化树为 pdf 格式
        with open(f"{name_file}_rooted.newick", 'w') as rooted_file:
            Phylo.write(tree, rooted_file, 'newick')

    def run_tree_50(self, tree_name):
        os.system(f"muscle -in {tree_name} -out {tree_name}.clw")
        os.system(f"FastTree {tree_name}.clw > {tree_name}.tree")

        with open(f"{tree_name}.tree", 'r') as file_new:
            hhh_list = []
            for hhh_line in file_new.readlines():
                one = hhh_line.split(")")[1:-1]
                hhh_list.extend([float(xxx.split(":")[0]) for xxx in one if xxx.split(":")[0] != ''])
            if (np.array(hhh_list) > 0.5).all():
                with open(f'{tree_name}_50.tree', 'w') as hhh_file:
                    hhh_file.write(str(hhh_line))
                self.draw_tree(f"{tree_name}_50.tree")

    def run(self):
        sp_geneid_dict = self.pep_files_ids()
        self.write_tree_file(sp_geneid_dict)
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:  # (可改) - 最大进程数
            executor.map(self.run_tree_50, glob.glob(os.path.join("output", "*.txt")))

# 构建列表系统发育树 - draw_list_tree_run_tools
def draw_list_tree_run_tools(place, patten):
    cmd = f"cd {path_get}/file_keep/{place}"
    subprocess.run(cmd, shell=True, check=True)

    tree = ListTree(glob.glob("orthomcl/*.pep"), "list.txt", additional_parameter=patten)
    tree.run()
    shutil.rmtree("*.zip", ignore_errors=True)
    os.system(f"cd {os.path.join(os.getcwd(), 'output')} && zip -r ../list_tree_BS_50_root_png.zip *.png")
    os.system(f"cd {os.path.join(os.getcwd(), 'output')} && zip -r ../list_tree_BS_50_root_file.zip *rooted.newick")


# species_classification_run_tools
def get_taxonomy_info(taxon_name, result_file, email, api_key):
    Entrez.email = email
    Entrez.api_key = api_key

    search_handle = Entrez.esearch(db="taxonomy", term=taxon_name, retmode="xml")
    search_results = Entrez.read(search_handle)
    search_handle.close()

    if "IdList" not in search_results or not search_results["IdList"]:
        print(f"No results found for the given taxon name: {taxon_name}")
        return

    taxon_id = search_results["IdList"][0]

    fetch_handle = Entrez.efetch(db="taxonomy", id=taxon_id, retmode="xml")
    taxonomy_data = Entrez.read(fetch_handle)
    fetch_handle.close()

    taxonomy_info = taxonomy_data[0]["LineageEx"]

    result_file.write(f"{taxon_name}:\t")
    for entry in taxonomy_info:
        rank = entry['Rank']
        scientific_name = entry['ScientificName']
        result_file.write(f"{scientific_name}\t")
    result_file.write(f"\n")
    time.sleep(1)  # 1秒的延迟

# species_classification_run_tools
def species_classification_run_tools(place):
    cmd = f"cd {path_get}/file_keep/{place}"
    subprocess.run(cmd, shell=True, check=True)
    email = "1457634627@qq.com"  # 改 - NCBI 的账号邮箱
    your_api_key = os.environ.get('NCBI_API_KEY', '')  # 改 - NCBI 账号的密钥
    with open("taxonomy_results.txt", "a") as result_file:  # 改 - 输出结果文件
        with open("sp_list.txt", 'r') as file_open:  # 改 - 输入物种列文件
            for line in file_open.readlines():
                plant_name = line.strip()  # 移除行尾的换行符等空白字符
                get_taxonomy_info(plant_name, result_file, email, your_api_key)


def GF_ks_circos_run_tools(place, sp_name):
    write_txt = (str("[excircle]") + "\n" + str(f"savefig = {sp_name}.genefam.png") + "\n" + str(
        f"specieslist = {sp_name}") + "\n" + str(f"lens_file = {sp_name}.lens.txt") + "\n" + str(
        f"gff_file = {sp_name}.new.gff") + "\n" + str(f"ks_file = {sp_name}_{sp_name}.ks.txt") + "\n" + str(
        f"pair_file = {sp_name}.pair") + "\n" + str(f"classifyfile  = {sp_name}.class") + "\n" + str("classify_color = 1:  # CC99FF,2:orange,3:#FF1493,4:red,5:blue,6:c,7:black") + "\n" + str(
        f"young_genes_ks = #") + "\n" + str("young_genes_color = #") + "\n" + str("axes_limit = 0.9") + "\n" + str("alpha = 0.7") + "\n" + str("line_color = # dcdcdd") + "\n" + str("label_pos = 0.85") + "\n" + str("dpi = 600"))

    text_create(f'excircle_{sp_name}', str(write_txt), place)
    cmd = f"""
        cd {path_get}/file_keep/{place}
        python .../run.py excircle -c excircle_{sp_name}.conf
    """
    subprocess.run(cmd, shell=True, check=True)


def get_counts(fn_gff):
    counts = {"gn": 0, "gs": 0, "en": 0, "es": 0, "un": 0, "us": 0, "mn": 0, "ms": 0, "in_": 0, "is_": 0, "cn": 0, "cs": 0}
    deal = ("#", " ", "\n")
    with open(fn_gff) as f:
        for line in f:
            if line.startswith(deal):
                continue
            a = line.split()
            # print(a[2])
            if a[2] == "gene":
                counts["gn"] += 1
                counts["gs"] += abs(int(a[4]) - int(a[3])) + 1
            elif a[2] == "mRNA":
                counts["mn"] += 1
                counts["ms"] += abs(int(a[4]) - int(a[3])) + 1
            elif a[2] == "exon":
                counts["en"] += 1
                counts["es"] += abs(int(a[4]) - int(a[3])) + 1
            elif a[2] == "CDS":
                counts["cn"] += 1
                counts["cs"] += abs(int(a[4]) - int(a[3])) + 1
            elif "UTR" in a[2]:
                counts["un"] += 1
                counts["us"] += abs(int(a[4]) - int(a[3])) + 1
    if counts["en"] == 0:
        with open(fn_gff) as f:
            ls = 0
            le = 0
            for line in f:
                if line.startswith(deal):
                    continue
                a = line.split()
                if "UTR" in a[2] or a[2] == "CDS":
                    counts["en"] += 1
                    counts["es"] += abs(int(a[4]) - int(a[3])) + 1
                    if abs(ls - int(a[4])) == 1 or abs(le - int(a[3])) == 1:
                        counts["en"] -= 1
                    ls = int(a[3])
                    le = int(a[4])
    counts["in_"] = counts["en"] - counts["mn"]
    counts["is_"] = counts["ms"] - counts["es"]
    return list(counts.values())


class FabaceaeTaxaForm(forms.Form):
    scientfiicname = forms.CharField(label='scientfiic_name', max_length=255)

























# blast
def blast_run_tools_re(place, patten, e, email, score, identity, myFile1, myFile2, nucl_or_prot):
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        makeblastdb -in {myFile1} -dbtype {nucl_or_prot} -parse_seqids -out dbname
        {patten} -query {myFile2} -db dbname -outfmt 5 -evalue {e} -out result_2.fasta -num_threads 8
    """
    os.system(cmd)




# cd_hit_run
def cd_hit_run_tools(place, email, similar, patten):
    """
    cd-hit -i db -o db90 -c 0.9 -n 5 -M 16000 -d 0 -T 8
        -i 输入文件，fasta格式的序列
        -o 输出文件路径和名字
        -c 相似性（clustering threshold），0.9表示相似性大于等于90%的为一类
        -n 两两序列进行序列比对时选择的 word size
        -d 0表示使用 fasta 标题中第一个空格前的字段作为序列名字
        -M 16000，16GB RAM
        -T 使用的线程数
        Choose of word size:
        -n 5 for thresholds 0.7 ~ 1.0
        -n 4 for thresholds 0.6 ~ 0.7
        -n 3 for thresholds 0.5 ~ 0.6
        -n 2 for thresholds 0.4 ~ 0.5
        -aL：控制代表序列比对严格程度的参数，默认为0，若设为0.8则表示比对区间要占到代表（长）序列的80%。
        -AL：控制代表序列比对严格程度的参数，默认为99999999，若设为40则表示代表序列的非比对区间要短于40bp。
        -aS：控制短序列比对严格程度的参数，默认为0，若设为0.8则表示比对区间要占到短序列的80%。
        -AS：控制短序列比对严格程度的参数，默认为99999999，若设为40则表示短序列的非比对区间要短于40bp。
    """
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        cd-hit -i 1.fasta -o cd_hit_result.fasta -c {similar} -n {patten} -d 0 -T 1
    """
    os.system(cmd)

    files = 'cd_hit_result.fasta.clstr cd_hit_result.fasta'
    zip_file(email=email, place=place, files=files)






# orthofinder
def orthfinder_run_tools(place, email, gene_tree, blast, alignment, tree_way, number):
    # -M    基因树推断方法（默认为dendroblast）可选：dendroblast ，msa
    # -S    序列比对使用的程序 （默认为Blast）可选：blast, mmseqs, blast_gz, diamond（推荐使用diamond，比对速度快）
    # # -A    多序列联配方式，该选项仅当 - M    msa    选项时才有效（默认为mafft）可选：muscle, mafft
    # # -T    建树方式，该选项仅当 - M    msa    选项时才有效 （默认为fasttree）可选：iqtree, raxml - ng, fasttree, raxml
    # -I    设定MCL的膨胀系数（默认为1.5）
    if gene_tree == str("msa"):
        cmd = f"""
            source /etc/profile
            cd {path_get}/file_keep/{place}
            orthofinder -f orthomcl -M {gene_tree} -S {blast} -A {alignment} -T {tree_way} -I {number} 
        """
        os.system(cmd)
    else:
        cmd = f"""
            source /etc/profile
            cd {path_get}/file_keep/{place}
            orthofinder -f orthomcl/ -M {gene_tree} -S {blast} -I {number} 
        """
        os.system(cmd)

    cmd2 = f"""
        cd {path_get}/file_keep/{place}/orthomcl/OrthoFinder
        zip -r result.zip *
        mv result.zip ../../
    """
    os.system(cmd2)

    g = f'{path_get}/file_keep/{place}/result.zip'
    youjian(a=email, b=g, place=place)





# phyml
def phyml_run_tools(email, place, patten, nice, model, frequency, num, small):
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        phyml -i 1.phy -d {patten} -b {num} -m {small} -f {frequency} -v e -a e -o {nice}
    """
    os.system(cmd)

    files = "1.phy_*"
    zip_file(email=email, place=place, files=files)


# paml_deal
def paml_run_one(patten, small, path, email, place):
    file_data = ""
    codeml_file = open(f'{path_get}/file_keep/paml/{patten}/{small}/codeml.ctl', 'r')
    for line in codeml_file.readlines():
        hh = re.sub(r'\d{9,}', f'{path}', line)
        file_data += hh
    co_new = open(f'{path_get}/file_keep/paml/{patten}/{small}/codeml.ctl', 'w')
    co_new.write(file_data)


# paml
def paml_run_two(place, email, patten, small):
    cmd = f"""
        source /etc/profile
        cd {path_get}/file_keep/{place}
        codeml ../paml/{patten}/{small}/codeml.ctl
    """
    os.system(cmd)

    g = '%s/file_keep/%s/resoult.txt' % (path_get, place)
    youjian(a=email, b=g, place=place)


# ================================= gfca end  ==============================================


# ================================= tools start =============================================


# dotplot
def dotplot_run_tools(place, email, evalue, score, hitnum, repnum, heng_chromosomes, shu_chromosomes, heng_species, shu_species, blast_name, shu_gff_name, heng_gff_name, shu_len_name, heng_len_name):
    global path_get
    # perl ../programs/dotplot.pl 1e-5 100 5 20 1_2_3 1_2_3 si.lens zm.lens si.gff zm.gff zm_si.blast zm si
    cmd = f"""
        cd {path_get}/file_keep/{place}
        perl ../programs/dotplot.pl {evalue} {score} {hitnum} {repnum} {heng_chromosomes} {shu_chromosomes} {shu_len_name} {heng_len_name} {shu_gff_name} {heng_gff_name} {blast_name} {heng_species} {shu_species} 
    """
    os.system(cmd)

    g = f'{path_get}/file_keep/{place}/result.png'
    youjian(a=email, b=g, place=place)



class MysqlGffLensBlast:
    def __init__(self, host, user, password, port, database, sp_one, sp_two):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.database = database
        self.sp_one = sp_one
        self.sp_two = sp_two

    def connect_and_fetch_data(self, table_name):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=self.database
            )
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            table_data = cursor.fetchall()
            cursor.close()
            connection.close()
            return table_data
        except Exception as e:
            print(f"Error: {e}")
            return None

    @staticmethod
    def get_spec_chr(spec_chr):
        spec_chr = re.sub('^\\D+', '', spec_chr)
        spec_chr = re.sub('^0', '', spec_chr)
        return spec_chr

    @staticmethod
    def gene_location(gff_file, lens_file, gl):
        len_pos, gff_pos = 1, 6
        chr_dict, chr_lens, loc_gene, n = {}, {}, {}, 0
        for li in lens_file:
            lis = list(li[1:])
            spec_chr = MysqlGffLensBlast.get_spec_chr(lis[0])
            chr_lens[spec_chr] = float(lis[len_pos])
            chr_dict[spec_chr] = float(n)
            n += float(lis[len_pos])
        total_lens = reduce(lambda x, y: int(x) + int(y), chr_lens.values())
        step = gl / total_lens

        for li in gff_file:
            lis = list(li[1:])
            spec_chr = MysqlGffLensBlast.get_spec_chr(lis[0])
            if spec_chr not in chr_dict:
                continue
            loc = (chr_dict[spec_chr] + float(lis[gff_pos])) * step
            loc_gene[lis[5]] = loc
        return loc_gene, step, chr_lens

    @staticmethod
    def getnewblast(blast, score, evalue, repnum, loc_1, loc_2):
        newblast = {}
        for li in blast:
            lis = list(li[1:])
            if not all((float(lis[11]) >= score, float(lis[10]) < evalue, lis[0] != lis[1])):
                continue
            if not all((lis[0] in loc_1, lis[1] in loc_2)):
                continue
            if lis[0] in newblast and lis[1] in newblast[lis[0]]:
                continue
            if lis[0] in newblast and len(newblast[lis[0]]) < repnum:
                newblast[lis[0]].append(lis[1])
            else:
                newblast[lis[0]] = [lis[1]]
        return newblast

    @staticmethod
    def pair_positon(blast, loc1, loc2):
        pos1, pos2, newcolor = [], [], []
        gl_start1, gl_start2 = 11 / 12, 1 / 12
        colors = ['red', 'blue', 'white']  # Change - Colors
        hitnum = 5  # Change - Colors
        for k, v in blast.items():
            for i in range(len(v)):
                if i == 0:
                    color = colors[0]
                elif i <= hitnum:
                    color = colors[1]
                else:
                    color = colors[2]
                pos1.append(gl_start2 + loc2[v[i]])
                pos2.append(gl_start1 - loc1[k])
                newcolor.append(color)
        return pos1, pos2, newcolor

    def process_data(self):
        adu_aev_blast_data = self.connect_and_fetch_data(f"{self.sp_one}_{self.sp_two}_blast")
        adu_gff_data = self.connect_and_fetch_data(f"{self.sp_one}_gff")
        aev_gff_data = self.connect_and_fetch_data(f"{self.sp_two}_gff")
        adu_lens_data = self.connect_and_fetch_data(f"{self.sp_one}_lens")
        aev_lens_data = self.connect_and_fetch_data(f"{self.sp_two}_lens")

        gl1, gl2 = 5 / 6, 5 / 6
        score, evalue, repnum = 100, 1e-5, 20  # Change - Adjust values
        gene_loc_1, step1, chr1_lens = self.gene_location(adu_gff_data, adu_lens_data, gl1)
        gene_loc_2, step2, chr2_lens = self.gene_location(aev_gff_data, aev_lens_data, gl2)
        blast = self.getnewblast(adu_aev_blast_data, score, evalue, repnum, gene_loc_1, gene_loc_2)
        x, y, colors = self.pair_positon(blast, gene_loc_1, gene_loc_2)
        return gene_loc_1, step1, chr1_lens, gene_loc_2, step2, chr2_lens, x, y, colors


# AKRUP
def akrup_run_blast_run_tools(place, e_value, max_target_seqs, outfmt, querypep_name, subjectpep_name):
    re_blast = f"{querypep_name}".split('.')[0] + "_" + f"{subjectpep_name}".split('.')[0]
    write_txt = (
            str("[blast]") + "\n" +
            str("num_thread = auto") + "\n" +
            str(f"evalue = {e_value}") + "\n" +
            str(f"outfmt = {outfmt}") + "\n" +
            str(f"max_target_seqs = {max_target_seqs}") + "\n" +
            str(f"querypep = {querypep_name}") + "\n" +
            str(f"subjectpep = {subjectpep_name}") + "\n" +
            str(f"outblast = {re_blast}.blast")
    )
    text_create('run_blast.conf', str(write_txt), place)
    cmd = f"""
        soruce /etc/profile
        cd {path_get}/file_keep/{place}
        AKRUP -rb run_blast.conf
    """
    subprocess.run(cmd, shell=True, check=True)


