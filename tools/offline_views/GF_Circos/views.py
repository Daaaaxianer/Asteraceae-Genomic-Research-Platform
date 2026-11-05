import os
import time
import uuid
import glob
import zipfile
import traceback

from django.shortcuts import render
from django.http import HttpResponse, FileResponse

try:
    from .tools import GF_ks_circos_run_tools
except ImportError:
    print("Error: tools.py not found or circular import.")
    traceback.print_exc()


def get_real_base_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    offline_views_dir = os.path.dirname(current_dir)
    tools_dir = os.path.dirname(offline_views_dir)
    project_root = os.path.dirname(tools_dir)
    return project_root


path_get = get_real_base_dir()

required_dirs = ['file_keep', os.path.join('file_keep', 'species_data')]
for d in required_dirs:
    os.makedirs(os.path.join(path_get, d), exist_ok=True)


def name_set():
    folder_name = f"{int(time.time())}_{str(uuid.uuid4())[:4]}"
    from api.download_access import create_job_directory
    create_job_directory(os.path.join(path_get, 'file_keep', folder_name))
    return folder_name


def keep_file(file_obj, folder_name):
    if not file_obj:
        return None

    target_dir = os.path.join(path_get, 'file_keep', folder_name)
    file_path = os.path.join(target_dir, file_obj.name)
    with open(file_path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    return file_path


def render_gf_circos_page(request, error_message=None):
    context = {}
    if error_message:
        context['error_message'] = error_message
    return render(request, 'GF_ks_circos.html', context)


def zip_and_respond(folder_name, files, download_name="result.zip"):
    target_dir = os.path.join(path_get, 'file_keep', folder_name)
    zip_filepath = os.path.join(target_dir, 'result.zip')

    file_list = []
    if '*' in files:
        search_pattern = os.path.join(target_dir, files.strip())
        file_list.extend(glob.glob(search_pattern))
    else:
        for fname in files.split():
            full_path = os.path.join(target_dir, fname)
            if os.path.exists(full_path):
                file_list.append(full_path)

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in file_list:
                zf.write(file_path, arcname=os.path.basename(file_path))

        if not os.path.exists(zip_filepath):
            return HttpResponse("Error: Zip file generation failed.", status=500)

        response = FileResponse(open(zip_filepath, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{download_name}"'
        response['Content-Type'] = 'application/zip'
        response.set_cookie('gf_circos_download', 'done', max_age=60, path='/')
        return response
    except Exception as e:
        traceback.print_exc()
        return HttpResponse(f"Error packing files: {e}", status=500)


def process_gf_circos_request(request):
    try:
        ks_file = request.FILES.get('ks_file')
        pair_file = request.FILES.get('pair_file')
        classify_file = request.FILES.get('classify_file')
        gff_file = request.FILES.get('gff_file')
        lens_file = request.FILES.get('lens_file')

        if not all([ks_file, pair_file, classify_file, gff_file, lens_file]):
            return render_gf_circos_page(request, error_message="Please upload all required files.")

        folder_name = name_set()

        ks_file.name = "Sob_Sob.ks.txt"
        pair_file.name = "Sob.pair"
        classify_file.name = "Sob.class"
        gff_file.name = "Sob.new.gff"
        lens_file.name = "Sob.lens.txt"
        sp_name = "Sob"

        keep_file(ks_file, folder_name)
        keep_file(pair_file, folder_name)
        keep_file(classify_file, folder_name)
        keep_file(gff_file, folder_name)
        keep_file(lens_file, folder_name)

        GF_ks_circos_run_tools(place=folder_name, sp_name=sp_name)
        download_filename = f"GF_Circos_Result_{folder_name}.zip"
        return zip_and_respond(folder_name, f"{sp_name}.genefam.png", download_name=download_filename)
    except Exception as e:
        traceback.print_exc()
        return render_gf_circos_page(request, error_message=f"Error during processing: {str(e)}")


def GF_ks_circos(request):
    if request.method == 'POST':
        return process_gf_circos_request(request)
    return render_gf_circos_page(request)


def GF_ks_circos_run(request):
    return process_gf_circos_request(request)
