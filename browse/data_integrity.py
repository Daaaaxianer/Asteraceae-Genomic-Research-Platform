"""Project data projections shared by display and export paths."""
import json
import math
import re
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.db import connection
from django.shortcuts import render


def expression_projection(columns, records):
    """Locate the unit by name; retain every actual sample in schema order."""
    gene = next(c for c in columns if c.lower() == 'geneid')
    unit = next(c for c in columns if c.lower() == 'express_index')
    samples = [c for c in columns if c not in (gene, unit)]
    positions = [columns.index(c) for c in [gene, unit] + samples]
    rows = [[record[i] for i in positions] for record in records]
    heatmap = []
    for row in rows:
        values = []
        for value in row[2:]:
            try:
                value = float(value)
                values.append(math.log2(value + 1) if math.isfinite(value) and value >= 0 else None)
            except (TypeError, ValueError):
                values.append(None)
        heatmap.append(values)
    return ['Gene ID', 'Unit'] + samples, rows, heatmap


def expression_page(request):
    from . import views
    with connection.cursor() as cursor:
        cursor.execute('SHOW TABLES')
        tables = {r[0] for r in cursor.fetchall()}
    codes = sorted(t[:-len('_express_table')] for t in tables if t.endswith('_express_table'))
    labels = {'Aann': 'Artemisia annua', 'Aary': 'Artemisia argyi', 'Amtr': 'Ambrosia trifida',
              'Arla': 'Arctium lappa', 'Cati': 'Carthamus tinctorius', 'Ccar': 'Cynara cardunculus',
              'Chmo': 'Chrysanthemum morifolium', 'Chna': 'Chrysanthemum nankingense',
              'Cich': 'Cichorium intybus', 'Cien': 'Cichorium endivia', 'Cind': 'Chrysanthemum indicum',
              'Enbr': 'Erigeron breviscapus', 'Hean': 'Helianthus annuus', 'Mimi': 'Mikania micrantha',
              'Smso': 'Smallanthus sonchifolius', 'Soca': 'Solidago canadensis', 'Stre': 'Stevia rebaudiana',
              'Tako': 'Taraxacum koksaghyz', 'Tamo': 'Taraxacum mongolicum'}
    context = {'expression_species': [(s, labels.get(s, s)) for s in codes]}
    species = (request.POST.get('sp_data_1') or '').strip()
    if request.method != 'POST':
        return render(request, 'geneExpression.html', context)
    species = 'Aary' if species == 'Aarg' else species
    if species not in codes:
        context['error'] = 'Expression data are not available for this dataset.'
        return render(request, 'geneExpression.html', context)
    query = (request.POST.get('query_sequence') or '').strip()
    if query:
        output = str(Path(views.path_get) / 'file_keep' / views.name_set())
        blast, genes = views._run_selected_species_blast(query, output, species)
        context['blast_results'] = blast
    else:
        genes = list(dict.fromkeys((request.POST.get('geneid') or '').split()))
    if not genes:
        context['error'] = 'Please enter a gene ID or protein sequence.'
        return render(request, 'geneExpression.html', context)
    table = species + '_express_table'
    unit = (request.POST.get('expression_index') or 'FPKM').strip()
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM `' + table + '` WHERE geneid IN (' +
                       ','.join(['%s'] * len(genes)) + ') AND Express_index = %s', genes + [unit])
        records = cursor.fetchall()
        columns = [c[0] for c in cursor.description]
    headers, rows, heatmap = expression_projection(columns, records)
    context.update(result=rows, expression_columns=headers,
                   not_found_geneids=[g for g in genes if g not in {r[0] for r in rows}])
    if rows:
        import plotly.graph_objects as go
        fig = go.Figure(go.Heatmap(z=heatmap, x=headers[2:], y=[r[0] for r in rows],
                                 colorscale=[[0, '#0005F1'], [.5, '#E6E8F0'], [1, '#F80300']],
                                 colorbar={'title': 'log2(value + 1)'}))
        fig.update_layout(title='Gene Expression: log2(' + unit + ' + 1)',
                          xaxis_title='Sample', yaxis_title='Gene ID', height=max(400, len(rows) * 25))
        context['plot_html'] = fig.to_html(full_html=False)
    return render(request, 'geneExpression.html', context)


def metabolite_image_path(root, identifier, cid, folder):
    """Reuse an existing structure only under the same PubChem CID."""
    if folder not in ('plant', 'scent'):
        return ''
    names = []
    identifier = str(identifier or '')
    cid = str(cid or '')
    # Existing Image values are CID_<number>; bare values cannot select paths.
    if re.fullmatch(r'CID_\d+', identifier) and (
            not re.fullmatch(r'\d+', cid) or identifier == 'CID_' + cid):
        names.append(identifier)
    if re.fullmatch(r'\d+', cid):
        names.append('CID_' + cid)
    folders = [folder, 'scent' if folder == 'plant' else 'plant']
    for name in dict.fromkeys(names):
        for candidate_folder in folders:
            relative = 'image/pubchem/' + candidate_folder + '/' + name + '.png'
            if (Path(root) / 'static' / relative).is_file():
                return relative
    return ''


def available_analysis_links(payload, static_root):
    """Keep absent analysis results explicit instead of offering dead downloads."""
    pattern = re.compile(r'<a\b[^>]*\bhref=[\"\']([^\"\']+)[\"\'][^>]*>.*?</a>', re.I | re.S)
    root = Path(static_root).resolve()
    def substitute(match):
        href = unescape(match.group(1))
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc:
            return match.group(0)
        path = unquote(parsed.path)
        marker = 'static/'
        if marker not in path:
            return match.group(0)
        relative = path.split(marker, 1)[1]
        target = (root / relative).resolve()
        if root not in target.parents or not target.is_file():
            return '<span class="text-muted">Not available</span>'
        return match.group(0).replace(match.group(1), '/static/' + relative, 1)
    def transform(value):
        if isinstance(value, str):
            return pattern.sub(substitute, value)
        if isinstance(value, list):
            return [transform(item) for item in value]
        if isinstance(value, dict):
            return {key: transform(item) for key, item in value.items()}
        return value
    return transform(payload)


def statistics_page(request):
    """Read a dated snapshot computed from this project's current schema."""
    path = Path(settings.BASE_DIR) / 'browse' / 'data' / 'current_statistics.json'
    context = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    return render(request, 'statistics.html', context)
