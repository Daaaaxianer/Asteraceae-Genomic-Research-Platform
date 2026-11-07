# AGRP: Asteraceae Genomic Research Platform

Release: `v1.0.0`

## Overview

AGRP is a web platform for comparative, functional, and evolutionary genomics in Asteraceae. It brings together genome annotations, gene duplication and synteny resources, trait-related gene families, transcriptomic and metabolomic datasets, floral scent profiles, and ancestral genome reconstructions. Its tools support gene family analysis, sequence similarity searches, phylogenetic reconstruction, and genomic visualization. AGRP-Switch provides a shared search interface across the platform's omics resources.

The full online platform described on the homepage contains 156 plant genomes: 149 published Asteraceae genomes, the newly sequenced *Solidago canadensis* genome, and six outgroup species. It includes 3,137,213 protein-coding gene annotations, 180 trait-related gene families, 29 ancestral nodes, and 6,734 transcriptomes. These counts describe the full platform.

This source-code release contains the application code and frontend templates, with a local SQLite configuration for interface inspection. Many large datasets and supporting files used by the online platform have been omitted to reduce the archive size. The archive does not contain the complete production MySQL database, sequence libraries, alignment databases, or all precomputed results and indexes.

For the four research directories and their examples, see [Additional repository modules](#additional-repository-modules).

## Architecture and local evaluation

The application uses Python and Django, with a Bootstrap 5 interface built from HTML, CSS, and JavaScript. The production deployment uses MySQL. The local edition uses SQLite at `.private/local.sqlite3`, so basic interface inspection does not require a separate database server.

The SQLite database contains tables initialized for local testing. Modules that depend on the complete omics database or external bioinformatics tools require the corresponding data and software. Depending on the module, absent data can produce empty results or database and file errors. MySQL-specific queries also require a MySQL backend or adaptation for SQLite.

Static assets belong under `static/`, with their original directory structure. The available Bootstrap, image, font, and JavaScript files are included in this archive. Public API access rules remain configured for the deployed platform and may need adjustment for local evaluation.

## Quick start

The project has been tested locally on Windows with **Python 3.11.9**. Use Python 3.11 with the versions listed in `requirements.txt`. Native packages, particularly `mysqlclient`, may need operating-system build tools when a compatible wheel is unavailable.

Extract the archive and open a terminal in the project root, where `manage.py` and `requirements.txt` are located.

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of `python` in the installation and Django commands. This uses the environment directly without activation.

Linux or macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

SQLite is included with Python. The requirements retain MySQL packages for the code paths and deployments that use MySQL. External bioinformatics executables need separate installation. Email notifications use the AGRP_SMTP_FROM and AGRP_SMTP_PASSWORD environment variables; NCBI requests can use NCBI_API_KEY. Private credentials and partner API keys are excluded from this archive.

### 2. Generate local settings

The application reads its database configuration and Django `SECRET_KEY` from `.private/settings.json`.

With the virtual environment active, run this command from the project root. It creates a new secret key, configures the SQLite path for your computer, and creates the runtime directories. It replaces any existing `.private/settings.json`; save a copy first if you have customized that file. It preserves an existing `.private/local.sqlite3` database.

```bash
python -c "import json; from pathlib import Path; from django.core.management.utils import get_random_secret_key; root = Path.cwd(); private = root / '.private'; private.mkdir(exist_ok=True); config = {'SECRET_KEY': get_random_secret_key(), 'DATABASES': {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(private / 'local.sqlite3'), 'OPTIONS': {'timeout': 20}}}}; (private / 'settings.json').write_text(json.dumps(config, indent=2), encoding='utf-8'); [(root / name).mkdir(exist_ok=True) for name in ['.api_security_logs', '.api_security_state', '.api_download_owners', 'file_keep', 'static']]"
```

On Linux and macOS, restrict access to the private configuration before running Django:

```bash
chmod 700 .private
chmod 600 .private/settings.json
```

The loader checks these file permissions on Unix systems.

### 3. Initialize the database and check the application

```bash
python -X utf8 manage.py migrate
python -X utf8 manage.py check
```

Migrations create the SQLite database if it is absent and apply the included table definitions. Research datasets and externally maintained business tables must be supplied separately. Local checks have passed, and the homepage and admin login page have returned HTTP 200.

### 4. Start the development server

```bash
python -X utf8 manage.py runserver 127.0.0.1:8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in a browser. Press `Ctrl+C` to stop the server. If port 8000 is occupied, choose another port, such as 8001.

The `-X utf8` option enables Python's UTF-8 mode and avoids console encoding errors from Chinese text and symbols printed by some modules.

## Production deployment

A complete instance requires a database and data collection configured for your server.

1. Set up MySQL, import the required schema and research records, and update `DATABASES` in `.private/settings.json`. Django migrations alone do not restore the full research database.
2. Install the external programs required by the workflows you intend to run, such as BLAST+, DIAMOND, HMMER, MCScanX, ParaAT, KaKs_Calculator, and IQ-TREE. Update executable paths to match your installation.
3. Supply reference sequences, annotations, precomputed indexes, results, and genome browser tracks. Check all storage paths and directory permissions.
4. Restore the complete static assets and configure static and media file serving. Adapt the provided Gunicorn or uWSGI configuration to your server and reverse proxy.
5. Set a new secret key, `DEBUG = False`, appropriate `ALLOWED_HOSTS`, and HTTPS settings. Review the API's domain and proxy access rules for your deployment.

Use Django's development server for local testing. Public deployments require a production server configuration.

## Citation

Please cite the AGRP source-code archive when using this code in your work:

> *AGRP: Asteraceae Genomic Research Platform (source code).* Zenodo. DOI: [10.5281/zenodo.23968976](https://doi.org/10.5281/zenodo.23968976)

After publication, use the citation exported by the Zenodo record for the complete author list and release metadata.

The homepage lists the AGRP platform manuscript as:

> *An integrated platform facilitating comparative and functional genomic discoveries in the Asteraceae.* In revision.

A related research publication listed on the homepage is:

> Kong X. M., Zhang Y., Wang Z. Y., et al. (2023). Two-step model of paleohexaploidy, ancestral genome reshuffling and plasticity of heat shock response in Asteraceae. *Horticulture Research*, 10(6), uhad073. [https://doi.org/10.1093/hr/uhad073](https://doi.org/10.1093/hr/uhad073)

The Horticulture Research DOI identifies the related research article. It is separate from the platform manuscript and the Zenodo source-code archive DOI above.

## License

The original AGRP code and documentation in this release are distributed under the Apache License, Version 2.0 (SPDX: Apache-2.0). See [LICENSE](LICENSE) for the full terms and [NOTICE](NOTICE) for attribution.

Third-party components retain their original licenses. Biological datasets and externally supplied assets remain subject to their own terms; the software license does not grant rights to those materials.

## Contact and support

Wang Lab, North China University of Science and Technology

Email: [wangjinpeng@ncst.edu.cn](mailto:wangjinpeng@ncst.edu.cn)

Platform: [Asteraceae Genomic Research Platform](https://asteraceae.cgrpoee.top/)

For questions about data availability or a complete server installation, contact the laboratory with the module name and the data or software resources you need.

## Additional repository modules

The four directories below provide research workflows, reference materials, and examples alongside the Django application. Each directory has its own guide describing the inputs, dependencies, commands, and available results. The Django platform described above runs from the repository root.

| Directory | Main purpose | Included resources |
| --- | --- | --- |
| [Aster_AGR](Aster_AGR/README.md) | Ancestral candidate searches, gene tracing, and ancestor resource extraction. | Three tool modules, command-line adapters, relationship tables, AAK-I resources, and small examples. |
| [Aster_Api](Aster_Api/README.md) | Documentation for programmatic access to AGRP data and downloads. | Endpoint reference, parameters, request examples, access rules, and the API documentation HTML template. |
| [Aster_Collinearity](Aster_Collinearity/README.md) | Protein homology searches, collinear block identification, Ka/Ks calculation, and dot plots. | Analysis scripts, a species-name table, a selected precomputed plotting example, and reference figures. |
| [Aster_MGA](Aster_MGA/README.md) | Construction of a multiple-collinearity table using manually defined homologous regions. | An Elu–Ddev worked example with annotations, BLAST hits, blocks, region definitions, scripts, tables, and figures. |

### Aster_AGR: ancestral genome tools

The ancestral genome directory separates the two search modes of the `ancestral_chromosome` page from the scripts used to extract ancestor resources:

- [Ancestral Candidate Search](Aster_AGR/ancestral_candidate_search/README.md): search selected ancestor databases and retain all retrieved hits passing the E-value, bitscore, and identity thresholds.
- [Ancestral Gene Tracing](Aster_AGR/ancestral_gene_tracing/README.md): select the best extant gene hit for each query, then retrieve its recorded ancestral relationships from the Fli, Gehy, and Arla combined reference tables. The module also builds the neighborhood data used by the result viewer.
- [Ancestral Genome Extraction](Aster_AGR/ancestral_genome_extraction/README.md): select supported ancestor–extant mappings and extract or rename matching GFF, CDS, and protein records. The supplied AAK-I CDS is distributed as `AAKI.cds.gz`, with local decompression instructions.

Small examples demonstrate offline filtering, tracing, and resource extraction. Fresh sequence searches require the corresponding DIAMOND or BLAST+ databases. The supplied full AAK-I resources retain repeated identifiers; review the module's [identifier status](Aster_AGR/ancestral_genome_extraction/README.md#identifier-status) before using them as a reference that requires unique gene IDs.

### Aster_Api: API documentation

This directory documents the deployed API at `https://asteraceae.cgrpoee.top/api/`, covering Genomics, Geno-Syn, and Multi-Omics queries, public and analysis-result files, browser exports, and tool request routes. It describes request methods, parameters, pagination, access credentials, rate limits, and error responses, with examples for scripted use.

The directory contains the API guide and its HTML documentation template. The endpoint implementation belongs to the root `api/` package and the Django application; use the local or production setup above when deploying those services.

### Aster_Collinearity: homology, blocks, and Ks

The [pipeline guide](Aster_Collinearity/collinearity-pipeline/README.md) describes the sequence of BLASTP or DIAMOND searches, ColinearScan block identification, and Ka/Ks calculation, together with BLAST, block, and Ks dot plots. It specifies the prepared FASTA, gene annotation, chromosome gene-count, and intermediate file formats expected by the scripts.

The [Aoff–Ases example](Aster_Collinearity/examples/Aoff_Ases/README.md) uses selected precomputed records for *Asparagus officinalis* and *Angraecum sesquipedale*. It provides a small plotting demonstration and expected figures. Protein/CDS inputs and the external analysis tools are needed to run a fresh complete calculation; the precomputed example does not include those FASTA inputs.

### Aster_MGA: multiple collinearity example

The worked example compares *Elaeis guineensis* (`Elu`) with *Dendrobium devonianum* (`Ddev`). It combines collinear blocks with manually delineated homologous regions, labeled A1–A4, to construct an Elu-referenced multiple-collinearity table with up to four Ddev copy columns per Elu gene.

The workflow converts plot coordinates to gene-index coordinates, assigns blocks to the selected regions, builds and reformats the table, extracts its corresponding BLAST pairs, and plots the result. The directory includes the [region correspondences](Aster_MGA/regions/Elu_Ddev.correspondence.txt) and the [tab-separated table with missing values marked as dots](Aster_MGA/mc_table/Elu_v_Ddev.mc.tab.dot.txt), alongside the scripts and figures.

Python, pandas, matplotlib, and Perl are used for the documented steps; rerunning block detection also requires ColinearScan. Manual region selection is part of the workflow, so a fresh analysis requires reviewing the region boundaries for the genomes being compared.

Use each module's guide for its own working-directory and file-format conventions. The modules include selected research data and demonstrations, while the complete online platform still requires the production resources described above.
