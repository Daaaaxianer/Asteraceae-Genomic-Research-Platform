import os
import time
import traceback
import uuid
import shutil

from django.conf import settings
from django.shortcuts import render
from Bio import SeqIO


def get_upload_dir():
    base_dir = str(settings.BASE_DIR)
    path = os.path.join(base_dir, 'file_keep')
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def save_uploaded_file(file_obj):
    if not file_obj:
        return None, None

    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    base_path = get_upload_dir()
    target_dir = os.path.join(base_path, folder_name)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    file_path = os.path.join(target_dir, file_obj.name)
    with open(file_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)

    return folder_name, file_path


def render_mount_rate_page(request, result_content=None, error_message=None, chromosomes_num=12, excluded_num=2000):
    context = {
        'result_content': result_content,
        'error_message': error_message,
        'chromosomes_num': chromosomes_num,
        'excluded_num': excluded_num,
    }
    return render(request, 'GenomeMountRateCalculator.html', context)


def process_mount_rate_request(request):
    fa_path = None
    chromosomes_num = request.POST.get('chromosomes_num', 12)
    excluded_num = request.POST.get('excluded_num', 2000)

    try:
        file = request.FILES.get('file', None)
        if file is None:
            return render_mount_rate_page(
                request,
                error_message='Please upload a FASTA file.',
                chromosomes_num=chromosomes_num,
                excluded_num=excluded_num,
            )

        if file.size > 200 * 1024 * 1024:
            return render_mount_rate_page(
                request,
                error_message='File size exceeds the limit (200MB).',
                chromosomes_num=chromosomes_num,
                excluded_num=excluded_num,
            )

        _, fa_path = save_uploaded_file(file)

        excluded_num_int = int(excluded_num)
        chromosomes_num_int = int(chromosomes_num)

        gene_lengths = []
        for record in SeqIO.parse(fa_path, 'fasta'):
            seq_len = len(record.seq)
            if seq_len > excluded_num_int:
                gene_lengths.append(seq_len)

        if not gene_lengths:
            return render_mount_rate_page(
                request,
                error_message='No sequences found larger than the excluded length.',
                chromosomes_num=chromosomes_num,
                excluded_num=excluded_num,
            )

        gene_lengths.sort(reverse=True)
        top_genes = gene_lengths[:chromosomes_num_int]
        total_top_length = sum(top_genes)
        total_genome_length = sum(gene_lengths)
        ratio = 0 if total_genome_length == 0 else total_top_length / total_genome_length

        result_content = [[file.name, "{:.4f}".format(ratio)]]
        return render_mount_rate_page(
            request,
            result_content=result_content,
            chromosomes_num=chromosomes_num,
            excluded_num=excluded_num,
        )

    except ValueError:
        return render_mount_rate_page(
            request,
            error_message='Please enter valid numeric values.',
            chromosomes_num=chromosomes_num,
            excluded_num=excluded_num,
        )
    except Exception as e:
        traceback.print_exc()
        return render_mount_rate_page(
            request,
            error_message=f'Error: {str(e)}',
            chromosomes_num=chromosomes_num,
            excluded_num=excluded_num,
        )
    finally:
        if fa_path and os.path.exists(os.path.dirname(fa_path)):
            try:
                shutil.rmtree(os.path.dirname(fa_path))
            except Exception:
                pass


def GenomeMountRateCalculator(request):
    if request.method == 'POST':
        return process_mount_rate_request(request)
    return render_mount_rate_page(request)


def GenomeMountRateCalculator_run(request):
    return process_mount_rate_request(request)
