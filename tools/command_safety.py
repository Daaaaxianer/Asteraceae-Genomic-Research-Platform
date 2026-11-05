"""Validated tool arguments and shell-free execution for legacy web tools."""
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
from functools import wraps

from django.conf import settings


class ToolInputError(ValueError):
    pass


def guarded_tool_view(view):
    @wraps(view)
    def dispatch(request, *args, **kwargs):
        from django.http import JsonResponse
        try:
            return view(request, *args, **kwargs)
        except ToolInputError as error:
            return JsonResponse({'status': 'error', 'message': str(error)}, status=400)
        except subprocess.TimeoutExpired:
            return JsonResponse({'status': 'error', 'message': 'Calculation timed out.'}, status=504)
    return dispatch


BINARIES = {
    'ParaAT.pl': '/www/tools/ParaAT2.0/ParaAT.pl',
    'KaKs_Calculator': '/www/tools/soft_tools/KaKs_Calculator',
    'iqtree2': '/www/tools/soft_tools/iqtree2',
    'MCScanX': '/www/tools/soft_tools/MCScanX',
    'duplicate_gene_classifier': '/www/tools/MCScanX/duplicate_gene_classifier',
    'diamond': '/www/tools/soft_tools/diamond',
    'makeblastdb': '/wangjp/yuzijian/tools/ncbi-blast-2.15.0+/bin/makeblastdb',
    'blastn': '/wangjp/yuzijian/tools/ncbi-blast-2.15.0+/bin/blastn',
    'blastp': '/wangjp/yuzijian/tools/ncbi-blast-2.15.0+/bin/blastp',
    'blastx': '/wangjp/yuzijian/tools/ncbi-blast-2.15.0+/bin/blastx',
    'sed': '/usr/bin/sed', 'cut': '/usr/bin/cut', 'perl': '/usr/bin/perl',
}
PARAAT_FORMATS = ('axt', 'fasta', 'paml', 'codon', 'clustal', 'optional')
KAKS_METHODS = ('NG', 'LWL', 'LPB', 'MLWL', 'MLPB', 'GY', 'YN', 'MYN', 'MS',
                'MA', 'GNG', 'GLWL', 'GLPB', 'GMLWL', 'GMLPB', 'GYN', 'GMYN')
DIAMOND_SENSITIVITY = ('--fast', '--mid-sensitive', '--sensitive', '--more-sensitive',
                       '--very-sensitive', '--ultra-sensitive')


def choice(value, allowed, field):
    if value not in allowed:
        raise ToolInputError('Invalid ' + field + '.')
    return value


def identifier(value, field='species abbreviation'):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value):
        raise ToolInputError('Invalid ' + field + ': use letters, digits, underscores or hyphens.')
    return value


def iq_model(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9+_.,{}-]{0,127}', value):
        raise ToolInputError('Invalid substitution model.')
    return value


def bootstrap(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{1,4}', value) or not 0 <= int(value) <= 5000:
        raise ToolInputError('Bootstrap count must be between 0 and 5000.')
    return str(int(value))


def columns(value):
    # cut's field grammar: N, N-M, N-, -M, and comma-separated combinations.
    if not isinstance(value, str) or len(value) > 256:
        raise ToolInputError('Invalid column selection.')
    for part in value.split(','):
        if not re.fullmatch(r'(?:[1-9]\d{0,5}(?:-[1-9]\d{0,5}|-)?|-[1-9]\d{0,5})', part):
            raise ToolInputError('Invalid column selection.')
        if '-' in part and not part.startswith('-') and not part.endswith('-'):
            a, b = map(int, part.split('-'))
            if a > b:
                raise ToolInputError('Column ranges must be ascending.')
    return value


def job_directory(place):
    identifier(str(place), 'task directory')
    root = (Path(settings.BASE_DIR) / 'file_keep').resolve()
    selected = (root / str(place)).resolve()
    if selected.parent != root or not selected.is_dir():
        raise ToolInputError('Invalid task directory.')
    return selected


def tool_environment():
    env = os.environ.copy()
    directories = list(dict.fromkeys(str(Path(p).parent) for p in BINARIES.values()))
    env['PATH'] = os.pathsep.join(directories + [env.get('PATH', '')])
    return env


def run_tool(program, arguments, cwd=None, stdout=None):
    """Run a fixed executable; on timeout terminate its entire process group."""
    if program not in BINARIES:
        raise ToolInputError('Unsupported tool.')
    env = tool_environment()
    configured = getattr(settings, 'AGRP_TOOL_EXECUTABLES', {}).get(program)
    executable = configured or (BINARIES[program] if os.name != 'nt' else None)
    if not executable or not os.path.isfile(executable):
        executable = shutil.which(program, path=env['PATH'])
    if not executable:
        raise RuntimeError('Required calculation tool is unavailable.')
    args = [str(a) for a in arguments]
    if any('\0' in a for a in args):
        raise ToolInputError('Invalid tool argument.')
    command = [executable] + args
    process = subprocess.Popen(command, shell=False, cwd=cwd, env=env,
                               stdin=subprocess.DEVNULL,
                               stdout=stdout if stdout is not None else subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=os.name != 'nt')
    try:
        output, errors = process.communicate(timeout=int(getattr(settings, 'AGRP_TOOL_TIMEOUT', 3600)))
    except BaseException:
        if os.name != 'nt':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.communicate()
        raise
    if process.returncode:
        # Do not put filenames, submitted input or tool stderr in HTTP errors.
        raise RuntimeError('Calculation failed. Check the input format and parameters.')
    return output


def execute_argv(command, cwd=None):
    if not isinstance(command, (list, tuple)) or not command:
        raise ToolInputError('Tool arguments must be a list.')
    return run_tool(str(command[0]), command[1:], cwd=cwd)


def mcscanx(place, file_name):
    identifier(file_name, 'input filename')
    cwd = job_directory(place)
    run_tool('MCScanX', [file_name], cwd=cwd)
    with (cwd / 'gene_classifier.txt').open('wb') as output:
        run_tool('duplicate_gene_classifier', [file_name], cwd=cwd, stdout=output)


def paraat(place, patten):
    choice(patten, PARAAT_FORMATS, 'alignment format')
    cwd = job_directory(place)
    # ParaAT reads the permitted processor count from a file.
    (cwd / 'processors.txt').write_text('2\n', encoding='ascii')
    run_tool('ParaAT.pl', ['-h', 'hom.homologs', '-n', 'cds.cds', '-a', 'pep.pep',
                         '-p', 'processors.txt', '-o', 'result', '-f', patten], cwd=cwd)
    with (cwd / ('result.' + patten)).open('wb') as output:
        for path in sorted((cwd / 'result').glob('*.' + patten)):
            if path.is_file() and path.resolve().parent == (cwd / 'result').resolve():
                with path.open('rb') as source:
                    shutil.copyfileobj(source, output)


def kaks(place, patten):
    choice(patten, KAKS_METHODS, 'KaKs method')
    run_tool('KaKs_Calculator', ['-i', 'kaks.axt', '-o', 'result_kaks.txt', '-m', patten],
             cwd=job_directory(place))


def iqtree(place, patten, bs_num):
    model, count = iq_model(patten), bootstrap(bs_num)
    args = ['-s', 'result.phy', '-m', model, '-nt', '2', '-redo']
    if int(count):
        args += ['-bb', count, '-bnni']
    run_tool('iqtree2', args, cwd=job_directory(place))


def find_replace(place, old_name, new_name):
    # Keep sed BRE and replacement semantics, but supply the script as one argv.
    # Escaping '/' prevents input from adding a second sed command (e.g. /e).
    if not isinstance(old_name, str) or not old_name or len(old_name) > 1024:
        raise ToolInputError('Search text is required and must be at most 1024 characters.')
    if not isinstance(new_name, str) or len(new_name) > 1024:
        raise ToolInputError('Replacement text must be at most 1024 characters.')
    if any(c in old_name + new_name for c in ('\0', '\n', '\r')):
        raise ToolInputError('Search and replacement must be single-line text.')
    # Replace unescaped delimiters, preserving existing backslash escapes.
    def escaped(text):
        result, slashes = [], 0
        for char in text:
            if char == '/' and slashes % 2 == 0:
                result.append('\\')
            result.append(char)
            slashes = slashes + 1 if char == '\\' else 0
        # A trailing backslash must not escape the closing delimiter.
        if slashes % 2:
            raise ToolInputError('Text cannot end with an unpaired backslash.')
        return ''.join(result)
    script = 's/' + escaped(old_name) + '/' + escaped(new_name) + '/g'
    cwd = job_directory(place)
    with (cwd / 'result.txt').open('wb') as output:
        run_tool('sed', ['-e', script, '--', 'upload.txt'], cwd=cwd, stdout=output)


def extract_columns(place, row_num, row_name, row_last):
    selected = columns(row_num)
    identifier(row_name, 'input filename')
    identifier(row_last, 'input extension')
    cwd = job_directory(place)
    with (cwd / (row_name + '.new.' + row_last)).open('wb') as output:
        run_tool('cut', ['-f', selected, '--', row_name + '.' + row_last], cwd=cwd, stdout=output)
