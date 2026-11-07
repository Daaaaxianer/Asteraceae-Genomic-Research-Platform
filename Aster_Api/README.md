# AGRP API Documentation

The Asteraceae Genomic Research Platform (AGRP) provides APIs to programmatically access and batch-download data across the platform. Users can retrieve genome resources, comparative genomics data, and multi-omics datasets directly through custom scripts, browsers, or bioinformatics workflows.

[Platform website](https://asteraceae.cgrpoee.top/) · [Online API documentation](https://asteraceae.cgrpoee.top/api_documentation)

- **Base URL:** `https://asteraceae.cgrpoee.top/api/`
- **Version:** `1.0`
- **Methods:** `GET` for data queries; `GET` / `HEAD` for public and result file retrieval; `POST` for browser exports and tool submissions.
- **Data access:** Published data queries are read-only. Tool submissions may start analysis jobs.

## Contents

- [1. Overview](#sec_1)
- [2. Quick Start](#sec_2)
- [3. General Rules](#sec_3)
- [4. Health Check & IP](#sec_4)
- [5. Genomics APIs](#sec_5)
  - [5.1 Genome files](#sec_5_1)
  - [5.2 Annotation data](#sec_5_2)
  - [5.3 TE data](#sec_5_3)
- [6. Geno-Syn APIs](#sec_6)
  - [6.1 Ancestral files](#sec_6_1)
  - [6.2 Static JSON](#sec_6_2)
  - [6.3 Database queries](#sec_6_3)
- [7. Multi-Omics APIs](#sec_7)
- [8. Downloads & Exports](#sec_downloads)
  - [8.1 Public files](#sec_downloads_public)
  - [8.2 Result files](#sec_downloads_results)
  - [8.3 Browser exports](#sec_downloads_export)
  - [8.4 Tools & services](#sec_downloads_tools)
- [9. Rate Limits](#sec_8)
- [10. Error Responses](#sec_9)
- [11. Usage Examples](#sec_10)
- [12. Notes](#sec_11)

<a id="sec_1"></a>

## 1. Overview

The Asteraceae Genomic Research Platform (AGRP) provides RESTful APIs to programmatically access and download data across the platform. These endpoints allow you to retrieve and download datasets across our three core hubs: Genomics (genome resources and functional annotations), Geno-Syn (ancestral genomes and comparative genomics), and Multi-Omics (transcriptomes, pan-genomes, and metabolomics datasets) via standard HTTP requests or bioinformatics workflows.

- **Genomics Portal**: Species lists, genome file checks, CDS/PEP/GFF downloads, and functional annotations (KEGG, InterProScan, m6A, TE).
- **Geno-Syn Portal**: Ancestral genome files, collinearity records, dotplots, syntenic blocks, hierarchical alignments, and core gene sets.
- **Multi-Omics Portal**: Pan-genome tables, transcriptome sample JSONs, gene expression values (TPM), and plant/scent metabolomics records.

> Public data queries use GET and do not modify published datasets. Section 8 also covers public file retrieval, protected analysis results, browser exports, and tool request routes. Tool submissions use their own input fields and may start analysis jobs.

<a id="sec_2"></a>

## 2. Quick Start

All current API endpoints are under the following base URL:

```text
https://asteraceae.cgrpoee.top/api/
```

> Most command-line examples on this page use ordinary `curl`. Use `curl -4` only when checking or using an IPv4-based IP whitelist. API key requests do not require `-4`.

1. Choose the resource group you need, such as genome files, Genomics annotations, Geno-Syn comparative data, or Multi-Omics data.
2. Find the endpoint in the tables below and include all required parameters in the URL query string.
3. Add optional filters such as `limit`, `offset`, `q`, or `gene_id` only when they are needed.
4. Use `GET` for data queries and file downloads. File retrieval gateways also accept `HEAD`; exports and tool submissions use `POST` as described in section 8.

### Example: check and download a genome file

For file downloads, it is recommended to check the file first and then download it.

```bash
# 1. Check whether the file exists
curl -i "https://asteraceae.cgrpoee.top/api/files/genome/?species=Aann&type=cds"

# 2. Download the file
curl -L -o Aann.cds "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

### Example: query data with a limit

Paginated query endpoints default to 100 records. Public access is capped at 100 records per page; partner and trusted access may request up to 1,000 and 2,000 respectively, subject to resource-specific limits. Use a smaller `limit` for a quick preview.

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=5"
```

<a id="sec_3"></a>

## 3. General Rules

| Item | Rule | Example |
| --- | --- | --- |
| HTTP method | Data queries use `GET`. Public and result file gateways accept `GET` and `HEAD`. Browser exports and tool submissions use `POST`. | Check the method listed for each endpoint. |
| Response format | Most endpoints return JSON. Download endpoints return file streams when the requested file exists. | `application/json` or attachment download |
| Required parameters | Some endpoints require parameters such as `species`, `type`, `dataset`, `query_genome`, or `filename`. | `?species=Aann&type=cds` |
| Pagination | Paginated queries default to 100 records and offset 0. The public page limit is 100; partner and trusted caps are 1,000 and 2,000, subject to resource-specific limits. Offset must be between 0 and 100,000. Species, dataset, and transcriptome sample catalogues are not paginated. | `?limit=20&offset=40` |
| Search filters | Some endpoints support keyword or field filters such as `q`, `gene_id`, `species`, `database`, or `query_genome`. | `?q=Aann&limit=5` |
| File and name safety | Use the resource identifiers and relative file paths published by the platform. File gateways restrict directories and formats. URL-encode spaces in filenames and query values. | `Aann`, `AAKI`, `Dapi_white%20petal.json` |
| HTTPS entry point | Use the public HTTPS domain. Direct origin-server API requests are rejected. | `https://asteraceae.cgrpoee.top/api/` |

> Use only the filters listed for the selected resource. An unknown parameter may be ignored rather than rejected. For database queries, inspect the response's `filters` object to confirm which filters were applied.

<a id="sec_4"></a>

## 4. Health Check and Client IP

**Endpoint:** `GET` `/api/ping/`

Use this endpoint to check whether the AGRP API service is running.

#### Request

```bash
curl -H "Accept: application/json" "https://asteraceae.cgrpoee.top/api/ping/"
```

#### Response example

```json
{
  "status": "ok",
  "message": "AGRP API is running",
  "version": "1.0",
  "base_url": "https://asteraceae.cgrpoee.top/api/"
}
```

**Endpoint:** `GET` `/api/whoami/`

Use this endpoint to check the public client IP address detected by the AGRP API service. For IPv4 whitelist applications, use the IPv4 command below from the actual server or computer that will access AGRP, and send the returned IPv4 address to the AGRP team.

#### Request: check the detected IPv4 address

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"
```

#### Response example

```json
{
  "status": "ok",
  "detected_ip": "203.0.113.10",
  "ip_source": "CF-Connecting-IP",
  "is_private_or_local": false,
  "message": "This is the client IP address detected by the AGRP API for this request."
}
```

> If this endpoint is opened directly in a browser, the detected address may be IPv6 because many networks prefer IPv6 automatically. For IPv4 whitelist applications, please use `curl -4` from the actual server or computer that will access AGRP. If AGRP adds your IPv4 address to the whitelist, your later curl-based high-throughput requests should also use `-4` when the network might otherwise choose IPv6. A detected public IP address does not necessarily mean it is suitable for whitelist access. Campus networks, dormitory networks, public Wi-Fi, mobile hotspots, and personal broadband connections may use shared, dynamic, or temporary addresses. In these environments, please request an API key instead of IP whitelist access.

<a id="sec_5"></a>

## 5. Genomics APIs

Genomics APIs provide access to genome file resources and selected annotation datasets.

<a id="sec_5_1"></a>

### 5.1 Genome File APIs

These endpoints are used to list species, check whether genome files exist, and download genome files.

Supported file types: `cds`, `pep`, `lens`, `gff`.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genomics/species/` | List species with available genome resources. | None |
| `GET` `/api/files/genome/species/` | Alias endpoint for genome species resources. | None |
| `GET` `/api/files/genome/` | Check whether a genome file exists. | `species` required; `type` required. |
| `GET` `/api/download/genome/` | Download a genome file. | `species` required; `type` required. |

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genomics/species/"
curl -i "https://asteraceae.cgrpoee.top/api/files/genome/?species=Aann&type=lens"
curl -L -o Aann.lens "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=lens"
```

<a id="sec_5_2"></a>

### 5.2 Annotation and Functional Genomics APIs

These endpoints query public annotation and functional genomics records. Use `limit` to avoid returning too many records at once.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genomics/interproscan/` | Query InterProScan annotation data. | `species` required; optional `database`, `gene_id`, `gene_ids`, `q`, `limit`, `offset`. |
| `GET` `/api/genomics/kegg/` | Query KEGG annotation data. | `species` required; optional `gene_id`, `gene_ids`, `ko`, `q`, `limit`, `offset`. |
| `GET` `/api/genomics/regulatory-proteins/` | Query regulatory protein or transcription factor data. | Optional `species`, `type`, `family`, `gene_id`, `tf_name`, `hmm_acc`, `hmm_name`, `q`, `limit`, `offset`. |
| `GET` `/api/genomics/m6a/` | Query m6A-related gene information. | Optional `species`, `first_class`, `hmm_id`, `second_class`, `gene_id`, `pfam_id`, `clan`, `q`, `limit`, `offset`. |
| `GET` `/api/genomics/duplication-types/` | Query duplication type data. | Optional `species`, `type`, `gene_id`, `gene_ids`, `q`, `limit`, `offset`. |

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genomics/interproscan/?species=Aann&database=Pfam&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genomics/regulatory-proteins/?species=Aann&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genomics/m6a/?species=Aann&first_class=readers&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genomics/duplication-types/?species=Aann&limit=5"
```

<a id="sec_5_3"></a>

### 5.3 Transposable Elements APIs

These endpoints list species with available transposable element resources and query TE records for a selected species.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genomics/transposable-elements/species/` | List species with available TE JSON resources. | None |
| `GET` `/api/genomics/transposable-elements/` | Query TE records for one species. | `species` required; optional `filename`, `q`, `limit`, `offset`. Use `filename` to select one published JSON file when the full species directory exceeds the query budget. |

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genomics/transposable-elements/species/"
curl -i "https://asteraceae.cgrpoee.top/api/genomics/transposable-elements/?species=Artemisia_annua&limit=5"
```

<a id="sec_6"></a>

## 6. Geno-Syn APIs

Geno-Syn APIs provide access to comparative genomics resources, ancestral genome files, collinearity data, block data, hierarchical data, and selected gene datasets.

<a id="sec_6_1"></a>

### 6.1 Ancestral Genome File APIs

These endpoints are used to list ancestral genome datasets, check file availability, and download ancestral genome files.

Supported file types: `cds`, `pep`, `lens`, `gff`. Example datasets: `AAKI`, `AAKII`, `ACAK`, `ASAKI`, `CAAKI`, `CIAKI`.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genosyn/ancestral-genomes/` | List ancestral genome datasets and file availability. | None |
| `GET` `/api/files/ancestral/` | Check whether an ancestral genome file exists. | `dataset` required; `type` required. |
| `GET` `/api/download/ancestral/` | Download an ancestral genome file. | `dataset` required; `type` required. |

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/ancestral-genomes/"
curl -i "https://asteraceae.cgrpoee.top/api/files/ancestral/?dataset=AAKI&type=cds"
curl -L -o AAKI.cds "https://asteraceae.cgrpoee.top/api/download/ancestral/?dataset=AAKI&type=cds"
```

<a id="sec_6_2"></a>

### 6.2 Collinearity and Dotplot Static JSON APIs

These endpoints query static JSON resources used by collinearity and dotplot pages.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genosyn/collinear-kaks/` | Query collinearity and Ka/Ks records. | Optional `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/dotplots/` | Query dotplot records. | Optional `q`, `limit`, `offset`. |

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/collinear-kaks/?q=Aann&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/dotplots/?q=Hean&limit=5"
```

<a id="sec_6_3"></a>

### 6.3 Geno-Syn Database Query APIs

These endpoints query database-backed comparative genomics resources. Some endpoints require a resource-specific parameter, such as `query_genome`.

The `block-details` endpoint returns block-level records for the selected `query_genome`. Use `gene_id` or `block_id` only when you want to narrow the result to a known exact identifier.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genosyn/blocks/` | Query Aster-Blocks summary data. | `query_genome` required; optional `reference_genome`, `query_chromosome`, `reference_chromosome`, `block_id`, `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/block-details/` | Query block-level gene details. | `query_genome` required; optional `gene_id`, `gene_ids`, `block_id`, `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/hierarchical-alignments/` | Query hierarchical multiple genome alignment data. | Optional `reference`, `hhh_number`, `gene_id`, `q`, `limit`, `offset`. References: `Hean`, `Eupl`, `Vivi`, `Lssa`. |
| `GET` `/api/genosyn/hierarchical-genes/` | Query hierarchical gene data. | Optional `reference`, `species`, `chromosome`, `gene_id`, `gene_ids`, `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/evogenes/` | Query Aster-Evogenes data. | Optional `event`, `gene_id`, `gene_ids`, `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/orthologous/` | Query orthologous gene data. | Optional `gene_id`, `orthogroup`, `species`, `og_type`, `include_genes`, `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/gene-families/` | Query gene family data. | Optional `gene_id`, `gene_ids`, `species`, `function`, `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/rubber-genes/` | Query rubber biosynthesis gene data. | Optional `gene_id`, `gene_ids`, `species`, `function`, `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/inulin-genes/` | Query inulin metabolism gene data. | Optional `gene_id`, `gene_ids`, `species`, `function`, `q`, `limit`, `offset`. |

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/blocks/?query_genome=Aann&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/block-details/?query_genome=Aann&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/hierarchical-alignments/?reference=Hean&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/hierarchical-genes/?reference=Hean&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/evogenes/?event=ECH&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/orthologous/?limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/gene-families/?species=Aann&function=floral&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/rubber-genes/?limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/inulin-genes/?limit=5"
```

<a id="sec_7"></a>

## 7. Multi-Omics APIs

Multi-Omics APIs provide access to pan-genome, transcriptome, expression, and metabolomics resources.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/multiomics/pangenome/` | Query pan-genome records. | Optional `q`, `limit`, `offset`. |
| `GET` `/api/multiomics/transcriptome/samples/` | List available transcriptome sample JSON files. | Optional `q`. Returns all matching file names; `limit` and `offset` are not supported. |
| `GET` `/api/multiomics/transcriptome/sample/` | Read one transcriptome sample JSON file. | `filename` required. |
| `GET` `/api/multiomics/transcriptome/expression/` | Query transcriptome expression data. | `species` required; optional `gene_id`, `gene_ids`, `expression_index`, `limit`, `offset`. |
| `GET` `/api/multiomics/metabolomics/plant/` | Query plant metabolomics records. | Optional `cid`, `species`, `type`, `cas`, `formula`, `ko`, `gene_id`, `q`, `limit`, `offset`. Field filters apply when the dataset has a matching column. |
| `GET` `/api/multiomics/metabolomics/scent/` | Query scent metabolomics records. | Optional `cid`, `species`, `type`, `cas`, `formula`, `ko`, `gene_id`, `q`, `limit`, `offset`. Field filters apply when the dataset has a matching column. |

```bash
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/pangenome/?limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/samples/?q=petal"
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/sample/?filename=Dapi_white%20petal.json"
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/expression/?species=Aann&expression_index=TPM&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/metabolomics/plant/?limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/metabolomics/scent/?limit=5"
```

<a id="sec_downloads"></a>

## 8. Unified Downloads and Exports

Use these endpoints for published files, analysis results, and exports across the platform. Website download buttons use the same gateways. Paths shown in angle brackets are placeholders; use the relative paths or complete result links supplied by the platform.

<a id="sec_downloads_public"></a>

### 8.1 Public Files and Previews

| Method and endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET / HEAD` `/api/download/public/<source>/<path>` | Download a published file as an attachment. | Path values: `source` and the published relative `path`. |
| `GET / HEAD` `/api/files/public/<source>/<path>` | Read a published file inline, including chart and browser data. | Same source and path rules as public downloads. |

Supported sources are `static` for published data directories, `example` for example files, `jbrowse` for genome-browser files, and `static_assets` for downloadable images under `image/`. Only published directories and supported file formats can be retrieved. A source value does not grant access to arbitrary server files.

For `static`, published directories include `Species_data`, `ancestral_data`, `transcriptome_json`, `TE_json`, `syn_data`, and `example_file`. Use links from the relevant dataset or tool page for other available resources.

```bash
# Inspect a published sample file without downloading its body
curl -I "https://asteraceae.cgrpoee.top/api/files/public/static/transcriptome_json/Dapi_white%20petal.json"

# Download the same file
curl -L -o Dapi_white_petal.json "https://asteraceae.cgrpoee.top/api/download/public/static/transcriptome_json/Dapi_white%20petal.json"

# Read one byte range; a valid range returns 206 Partial Content
curl -H "Range: bytes=0-255" "https://asteraceae.cgrpoee.top/api/files/public/static/transcriptome_json/Dapi_white%20petal.json"
```

Public and result file gateways support HEAD and a single byte range. Responses include `Accept-Ranges: bytes`; a partial response includes `Content-Range`. Invalid or unsatisfiable ranges return 416. Direct links to published data under `/static/` and results under `/file_keep/` are unavailable; use the file gateways.

<a id="sec_downloads_results"></a>

### 8.2 Analysis Result Files

| Method and endpoint | Purpose | Access |
| --- | --- | --- |
| `GET / HEAD` `/api/download/result/<path>` | Download one result file. | Use the creating browser or API-key identity, or a complete issued file link. |
| `GET / HEAD` `/api/files/result/<path>` | Preview or read one result file inline. | The same result access rules apply. |

The browser that creates a job keeps its access marker automatically. Script clients should retain their cookies or use the same API key used to create the job. A file link issued by the platform can also be opened on another device; keep its complete `access_token` query value. The token may alternatively be sent in the `X-AGRP-Result-Token` request header.

Issued file links expire 7 days after the job directory is registered. Each link authorizes one file, so changing its filename does not grant access to another result. Missing, expired, or unauthorized result files return 404. An API key that raises a request quota does not grant access to another caller's jobs.

An authorized result-file response may include `X-AGRP-Result-Link` with a downloadable file link. Treat that complete link as a private access credential and share it only with intended recipients.

<a id="sec_downloads_export"></a>

### 8.3 Browser-Generated Exports

| Method and endpoint | Purpose | Request body |
| --- | --- | --- |
| `POST` `/api/download/export/` | Return an existing browser-generated table, image, or other supported file as an attachment. | `multipart/form-data` with one required `file` field; maximum file size 16 MiB. |

The submitted file is streamed back as an attachment and is not stored as a new analysis result. The filename must use a supported extension, such as `.tsv`, `.csv`, `.xlsx`, `.png`, `.svg`, or `.pdf`. A missing file or unsupported format returns 400; an oversized file returns 413. GET is not supported.

```bash
# chart.svg is an existing local file to export
curl -F "file=@chart.svg" -o exported_chart.svg "https://asteraceae.cgrpoee.top/api/download/export/"
```

<a id="sec_downloads_tools"></a>

### 8.4 Tool Requests, Downloads, and SequenceServer

Tool submission and download routes are listed below. Replace path placeholders with values issued for your job. Submission fields and response formats depend on the tool; use its tool documentation and retain the same cookies or API-key identity for subsequent result access.

<details>
<summary>GET: tool examples and job downloads (16)</summary>

Use the job identifier and download options supplied by the tool result page. The generic download route accepts the published file value issued by the platform.

```text
/api/download/browse/dupgen_job_download/<job_id>
/api/download/browse/dupgen_job_blast_download/<job_id>
/api/download/browse/kegg_job_download/<job_id>
/api/download/browse/kegg_job_blast_download/<job_id>
/api/download/browse/function_gene_job_download/<job_id>
/api/download/browse/function_gene_job_blast_download/<job_id>
/api/download/browse/ancestral_ks_dotplot_download/<job_id>
/api/download/browse/interproscan_job_download/<job_id>
/api/download/browse/interproscan_job_blast_download/<job_id>
/api/download/download/
/api/download/tools/example-download/<tool_name>/<filename>
/api/download/tools/wgdimcs_result_download/<place>
/api/download/tools/block_number_count_example_download
/api/download/tools/wgdi_result_download/<tool_name>/<place>
/api/download/tools/wgdi_blockinfo_download/<place>
/api/download/tools/interproscan_download
```

</details>

<details>
<summary>GET: table exports (6)</summary>

Add export=tsv and the filters supported by the corresponding table page.

```text
/api/download/browse/orthologous
/api/download/browse/hierarchical_alignments/<reference>/data/
/api/download/browse/hierarchical_alignments_Hean/data/
/api/download/browse/hierarchical_alignments_Lssa_all/data/
/api/download/browse/hierarchical_alignments_Vivi/data/
/api/download/browse/hierarchical_alignments_Eupl/data/
```

</details>

<details>
<summary>POST: tool submissions (69)</summary>

Send the upload and option fields documented for the selected tool. These routes may start calculations and have tool-specific responses.

```text
/api/download/tools/blast_run
/api/download/tools/diamond_run
/api/download/tools/blast_match_run
/api/download/tools/sequence_fetch_run
/api/download/tools/mcscanx_run
/api/download/tools/colinearscan_run
/api/download/tools/wgdimcs_run
/api/download/tools/synvisio_run
/api/download/tools/block_number_count_run
/api/download/tools/paraat_run
/api/download/tools/kaks_calculator_run
/api/download/tools/zu_ks_calculate_run
/api/download/tools/wgdikaks_run
/api/download/tools/zu_blast_dotplot_run
/api/download/tools/zu_block_dotplot_url
/api/download/tools/zu_ks_dotplot_run
/api/download/tools/wgdi_dotplot_run
/api/download/tools/wgdikaks_dot_run
/api/download/tools/zu_correspondence_mc_run
/api/download/tools/collinearity_generator_run
/api/download/tools/zu_retention
/api/download/tools/zu_loss_run
/api/download/tools/zu_pindex
/api/download/tools/draw_list_tree_run
/api/download/tools/wgdi_blockinfo_run
/api/download/tools/wgdi_correspondence_run
/api/download/tools/GC_calculation_run
/api/download/tools/chromosome_length_run
/api/download/tools/geme_cds_exon_counter_run
/api/download/tools/GenomeMountRateCalculator_run
/api/download/tools/GF_ks_circos_run
/api/download/tools/codonw_run
/api/download/tools/cpgfinder_run
/api/download/tools/meme_suit_run
/api/download/tools/hmmer_run
/api/download/tools/pfam_run
/api/download/tools/interproscan_run
/api/download/tools/sequence_alignment_run
/api/download/tools/fasttree_run
/api/download/tools/iq_tree_run
/api/download/tools/iTAK_run
/api/download/tools/phyml_run
/api/download/tools/draw_heatmap_run
/api/download/tools/lollipop_chart_run
/api/download/tools/draw_gene_structure_run
/api/download/tools/species_classification_run
/api/download/tools/sequence_screening_run
/api/download/tools/formatTofasta_run
/api/download/tools/find_replace_run
/api/download/tools/duplicate_removal_run
/api/download/tools/extract_column_run
/api/download/tools/file_merge_run
/api/download/tools/deal_star_run
/api/download/tools/subtree_extractor_run
/api/download/tools/bio_tools/web_tools/calculation/bdi_finder/
/api/download/tools/bio_tools/web_tools/calculation/bdi_extractor/
/api/download/tools/bio_tools/web_tools/calculation/bdi_combiner/
/api/download/tools/bio_tools/web_tools/calculation/bdi_deduplicator/
/api/download/tools/bio_tools/web_tools/calculation/ss_extractor/
/api/download/tools/bio_tools/web_tools/calculation/saf_converter/
/api/download/tools/bio_tools/web_tools/calculation/bbm_extraction/
/api/download/tools/bio_tools/web_tools/calculation/deal_stars/
/api/download/tools/bio_tools/web_tools/calculation/gene_stats/
/api/download/tools/bio_tools/web_tools/phylo/lollipop/
/api/download/tools/bio_tools/web_tools/phylo/iq_tree/
/api/download/tools/bio_tools/web_tools/phylo/ks_distriplot/
/api/download/tools/bio_tools/web_tools/homology/cds2geno_dotplot/
/api/download/tools/bio_tools/web_tools/synteny/mga_circos/
/api/download/tools/akrup_run_blast_run
```

</details>

Tabular exports use `export=tsv` with the orthologous or hierarchical-alignment export routes. Tool status and result pages retain their own page URLs. A background job's download becomes available after that job completes.

| Method and endpoint | Purpose | Request |
| --- | --- | --- |
| `GET` `/api/download/service/<service>/<path>` | Download a SequenceServer report. | `service=sequenceserver`; `path=download/<report_id>.<format>`. Use the report link supplied by SequenceServer. |
| `POST` `/api/download/service/sequenceserver/get_sequence` | Download selected SequenceServer sequences. | Use the selection fields provided by SequenceServer. Request body maximum: 2 MiB. |

The service gateway supports these two SequenceServer download operations. Tool submissions have additional rate and calculation-capacity limits; a 429 response can indicate that calculation slots are full. For browser POST requests, an Origin header, when present, must match the requested host.

<a id="sec_8"></a>

## 9. Rate Limits and Fair Use

Authentication is not required for published data queries and public file downloads. Analysis result access requires the creating browser or API-key identity, or a valid issued file link.

To maintain stable service for all users, API requests are rate-limited by client access level. Standard public users are limited by IP address. Authorized collaborators may receive higher quotas through registered IP addresses or dedicated API keys.

### Current public limits

| Endpoint group | Current public limit | Notes |
| --- | --- | --- |
| `/api/download/` | 5 requests per minute per IP; up to 2 concurrent download requests per IP. | Shared across all download gateways, including public files, results, exports, services, and tool request routes. The global download concurrency limit is 8. |
| `/api/files/` | 60 requests per minute per IP. | Shared by file checks and inline file reads. Public and result previews allow up to 8 concurrent reads per caller, with a global limit of 8. |
| `JBrowse file reads` | 600 requests per minute per caller. | Separate viewer rate for `/api/files/public/jbrowse/`; inline concurrency limits still apply. |
| `/api/genomics/` , `/api/genosyn/` , `/api/multiomics/` | 120 requests per minute per IP. | Applies to public JSON and database query endpoints. |
| `/api/ping/` | 60 requests per minute per IP. | Applies to the API health check endpoint. The client-IP endpoint uses the query quota. |
| `limit` parameter | Default: 100 records; public maximum: 100 records per page. | Large values such as `limit=999999` are automatically capped at 100 for public access. |

### Authorized high-throughput access

For large-scale batch access, authorized collaborators may be granted higher quotas by registering a fixed IP address or by using a dedicated API key. The API endpoints remain the same; authorized requests simply receive a higher access tier.

| Access type | How it works | Typical use case |
| --- | --- | --- |
| Registered IP address | The collaborator provides a fixed server IPv4 address or stable institutional server network range, and AGRP grants higher quota for requests from that address. If an IPv4 address is registered, requests must actually be sent through that IPv4 address; curl users can use `-4`. Personal computers on campus networks, dormitory networks, public Wi-Fi, mobile hotspots, or dynamic home broadband are generally not suitable for IP whitelist access. | Laboratory servers, institutional servers, or stable computing clusters. |
| Dedicated API key | The collaborator sends a key in the `X-AGRP-API-Key` request header. API keys should not be placed in the URL query string. | Teams without a fixed IP address, cross-institution workflows, or temporary authorized access. |
| Bulk package or manifest | For very large downloads, a curated package or file manifest may be more appropriate than sending many individual API requests. | Full dataset mirroring, long-term local analysis, or large-scale automated pipelines. |

### Checking the IP address for whitelist applications

Before requesting IPv4 whitelist access, run the following command from the actual fixed server that will access AGRP. This command forces IPv4 and avoids accidentally submitting an IPv6 address returned by a browser request.

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"
```

> The returned `detected_ip` is the client IP detected by AGRP for that request. However, a detected public IP is not always suitable for whitelist access. If the request comes from a campus network, dormitory network, public Wi-Fi, mobile hotspot, or personal dynamic broadband connection, use an AGRP API key instead.

### Using an approved IPv4 whitelist

If AGRP has approved and registered your IPv4 address, make sure your automated requests are sent through that same IPv4 address. For `curl`, add `-4` to high-throughput query or download commands when your network may otherwise prefer IPv6.

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000"

curl -4 -L -o Aann.cds "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

> This requirement applies to IPv4 whitelist access only. If you are using an AGRP API key, use the `X-AGRP-API-Key` header; `-4` is not required unless your own network policy needs it.

### Using an API key

If the AGRP team provides an API key, include it in the HTTP request header named `X-AGRP-API-Key`. Do not include the key in a URL parameter, browser address bar, or shared link.

```bash
curl -H "X-AGRP-API-Key: agrp_your_api_key_here" \
  "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000"

curl -H "X-AGRP-API-Key: agrp_your_api_key_here" \
  -L -o Aann.cds \
  "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

> If a request exceeds the current rate limit, the API returns `429 Too Many Requests`. Please wait briefly and retry with a lower request frequency. For repeated batch downloads or large automated workflows, contact the AGRP team for high-throughput access instead of sending high-frequency public requests.

Paginated public queries return at most 100 records per page; partner and trusted caps are 1,000 and 2,000. TE queries have an additional maximum of 1,000 records. The values `limit=all`, `none`, and `0` use the applicable finite page limit. A parsed JSON file must not exceed 16 MiB; one TE query may select at most 64 files and 16 MiB in total. Larger parsed-data requests return `413`. These query budgets do not cap streamed public file downloads at 16 MiB. API responses include `X-Request-ID` and `Cache-Control: private, no-store`.

### Recommended access pattern

- Check file availability before downloading large files.
- Use `limit` and `offset` for large tables instead of requesting all records at once.
- Avoid opening many parallel download connections from the same IP address.
- Use the `X-AGRP-API-Key` header only when an API key has been issued by the AGRP team.
- For full-dataset access, request a bulk package or manifest when possible.

<a id="sec_9"></a>

## 10. Error Responses

When a request is invalid or the requested resource does not exist, the API returns a JSON error response with an appropriate HTTP status code.

| Status | Meaning | Common cause |
| --- | --- | --- |
| `200` | OK | The request succeeded. |
| `206` | Partial Content | A file gateway returned the requested byte range. |
| `400` | Bad Request | Missing required parameter, invalid file type, or unsafe parameter value. |
| `403` | Forbidden | The request did not use the public API entry point, or a POST Origin header did not match the requested host. |
| `404` | Not Found | The resource is unavailable, unpublished, or not authorized for the caller. An expired result-file link also returns 404. |
| `405` | Method Not Allowed | The endpoint does not support the supplied HTTP method. |
| `413` | Content Too Large | A JSON/TE query, export file, or sequence-selection body exceeded its resource budget. |
| `414` | URI Too Long | The query string exceeded 8,192 characters. |
| `416` | Range Not Satisfiable | The requested file byte range was invalid or unavailable. |
| `426` | Upgrade Required | The API request did not use HTTPS. |
| `429` | Too Many Requests | A rate, concurrency, or calculation-capacity limit was reached. Wait for the interval in Retry-After before retrying. |
| `500 / 502 / 503` | Service error | The request or upstream service could not be completed. Retain X-Request-ID when reporting the failure. |

### 10.1 Missing required parameter

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/blocks/?limit=5"
```

```json
{
  "status": "error",
  "message": "Missing required parameter: query_genome"
}
```

Correct request:

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/blocks/?query_genome=Aann&limit=5"
```

### 10.2 Invalid file type

```bash
curl -i "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=abc"
```

```json
{
  "status": "error",
  "message": "Invalid type parameter.",
  "type": "abc",
  "allowed_types": ["cds", "pep", "lens", "gff"]
}
```

### 10.3 File not found

```bash
curl -i "https://asteraceae.cgrpoee.top/api/download/genome/?species=NotExist&type=cds"
```

```json
{
  "status": "error",
  "message": "File not found.",
  "species": "NotExist",
  "type": "cds",
  "filename": "NotExist.cds"
}
```

### 10.4 Invalid species parameter

```bash
curl -i "https://asteraceae.cgrpoee.top/api/download/genome/?species=../../etc/passwd&type=cds"
```

```json
{
  "status": "error",
  "message": "Invalid species parameter. Only letters, numbers, underscores, hyphens and dots are allowed.",
  "species": "../../etc/passwd"
}
```

### 10.5 Too many requests

If the request frequency or the number of concurrent downloads is too high, the API may return `429 Too Many Requests`.

```json
{
  "detail": "Request was throttled. Expected available in 42 seconds."
}
```

File-gateway rate limits use this response format:

```json
{
  "status": "error",
  "message": "Too many file requests. Retry later."
}
```

For concurrent download limits, the response may look like this:

```json
{
  "detail": "Too many concurrent download requests. Please wait for your current downloads to finish.",
  "access": "public",
  "max_concurrent_downloads": 2
}
```

Error responses can use `message` or `detail`, depending on the endpoint. Read the HTTP status and `Retry-After` header as well as the JSON body.

<a id="sec_10"></a>

## 11. Usage Examples

The examples below show common ways to use the API. Use the resource tables for query parameters and section 8 for file retrieval, exports, and tool-specific request routes.

### 11.1 Check your detected IPv4 address

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"
```

### 11.2 Check whether the API is available

```bash
curl -i "https://asteraceae.cgrpoee.top/api/ping/"
```

### 11.3 List genome resources and download a file

```bash
# List species with available genome files
curl -i "https://asteraceae.cgrpoee.top/api/genomics/species/"

# Check whether a specific file exists
curl -i "https://asteraceae.cgrpoee.top/api/files/genome/?species=Aann&type=cds"

# Download the file
curl -L -o Aann.cds "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

### 11.4 Query annotation records

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genomics/interproscan/?species=Aann&database=Pfam&limit=5"
```

### 11.5 Query Geno-Syn records

```bash
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/blocks/?query_genome=Aann&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/block-details/?query_genome=Aann&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/hierarchical-genes/?reference=Hean&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/evogenes/?event=ECH&limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/genosyn/gene-families/?species=Aann&function=floral&limit=5"
```

### 11.6 Query Multi-Omics records

```bash
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/pangenome/?limit=5"
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/samples/?q=petal"
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/sample/?filename=Dapi_white%20petal.json"
curl -i "https://asteraceae.cgrpoee.top/api/multiomics/metabolomics/plant/?limit=5"
```

<a id="sec_11"></a>

## 12. Notes

- Data query endpoints provide read-only access to published AGRP resources; exports and tool submissions use the methods listed in section 8.
- Download endpoints return file streams only when the requested file exists. For scripts, check file availability before downloading large files.
- Keep complete issued result-file links, including their access tokens. File links expire 7 days after job registration and authorize only the selected file.
- API requests may be rate-limited by IP address or authorized access level to maintain stable public service.
- Authorized collaborators may receive higher quotas through registered fixed server IPv4 addresses or the `X-AGRP-API-Key` request header.
- Use `curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"` to check the IPv4 address detected by AGRP before requesting IPv4 whitelist access.
- If your approved whitelist address is IPv4, make sure later curl-based high-throughput requests also use `-4` when the network may otherwise prefer IPv6.
- Paginated queries default to 100 records. Use `limit` and `offset` to page through results. Resource catalogues and individual sample JSON responses are not paginated.
- URL-encode filenames or query values that contain spaces, for example `Dapi_white%20petal.json`.
- An empty `data` list means no records were returned for the applied filters and offset; check pagination as well as filter values.
- This documentation describes programmatic access to public resources and does not replace the normal website pages.
