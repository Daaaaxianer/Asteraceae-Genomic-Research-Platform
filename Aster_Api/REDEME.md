# API Documentation

This page describes the public read-only APIs of the AGRP / Asteraceae Genomic Research Platform. Use these endpoints to download genome resources and retrieve public genomics, comparative genomics, and multi-omics data through scripts, browsers, or bioinformatics workflows.

- Base URL: `https://asteraceae.cgrpoee.top/api/`
- Method: `GET`
- Version: `1.0`
- Mode: read-only

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
- [8. Rate Limits](#sec_8)
- [9. Error Responses](#sec_9)
- [10. Usage Examples](#sec_10)
- [11. Notes](#sec_11)

<a id="sec_1"></a>

## 1. Overview

The AGRP public API provides structured access to selected platform resources. It can be used to list available datasets, check file availability, download genome-related files, and query public data tables or JSON resources.

- **Genome resources**: Species lists, genome file checks, and genome file downloads.
- **Geno-Syn resources**: Ancestral genome files, collinearity records, dotplots, blocks, hierarchical data, and gene sets.
- **Multi-Omics resources**: Pan-genome, transcriptome, expression, plant metabolomics, and scent metabolomics data.

> **Note:** The public API is read-only. Task-based services such as sequence submission, BLAST search, background analysis jobs, and generated result files are not included in this documentation.

<a id="sec_2"></a>

## 2. Quick Start

All current API endpoints are under the following base URL:

```text
https://asteraceae.cgrpoee.top/api/
```

> **Note:** All command-line examples in this page use `curl -4` to prefer IPv4. This is especially important when checking an IP address for whitelist applications, because browsers and some networks may prefer IPv6.

1. Choose the resource group you need, such as genome files, Genomics annotations, Geno-Syn comparative data, or Multi-Omics data.
2. Find the endpoint in the tables below and include all required parameters in the URL query string.
3. Add optional filters such as `limit`, `offset`, `q`, or `gene_id` only when they are needed.
4. Send a `GET` request with `curl`, a browser, Python, R, or another HTTP client.

### Example: check and download a genome file

For file downloads, it is recommended to check the file first and then download it.

```bash
# 1. Check whether the file exists
curl -4 -i "https://asteraceae.cgrpoee.top/api/files/genome/?species=Aann&type=cds"

# 2. Download the file
curl -4 -L -o Aann.cds "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

### Example: query data with a limit

For large query endpoints, use `limit` to return a manageable number of records. The default limit is 20 records. For public access, the maximum allowed limit is 100 records per request; authorized API-key users may have higher limit caps.

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=5"
```

<a id="sec_3"></a>

## 3. General Rules

| Item | Rule | Example |
| --- | --- | --- |
| HTTP method | All current endpoints use `GET`. | `curl -4 -i "URL"` |
| Response format | Most endpoints return JSON. Download endpoints return file streams when the requested file exists. | `application/json` or attachment download |
| Required parameters | Some endpoints require parameters such as `species`, `type`, `dataset`, `query_genome`, or `filename`. | `?species=Aann&type=cds` |
| Pagination | List endpoints usually support `limit` and `offset`. The default limit is 20. For public access, the maximum returned records per request is 100; authorized API-key users may have higher limit caps. | `?limit=20&offset=40` |
| Search filters | Some endpoints support keyword or field filters such as `q`, `gene_id`, `species`, `database`, or `query_genome`. | `?q=Aann&limit=5` |
| File and name safety | Download-related names use safe identifiers such as letters, numbers, underscores, hyphens, and dots. Filename values that contain spaces should be URL-encoded. | `Aann`, `AAKI`, `Dapi_white%20petal.json` |

> **Note:** If a request returns `400 Bad Request`, first check whether a required parameter is missing or whether the parameter name is incorrect.

<a id="sec_4"></a>

## 4. Health Check and Client IP

**Endpoint:** `GET` `/api/ping/`

Use this endpoint to check whether the AGRP API service is running.

#### Request

```bash
curl -4 -H "Accept: application/json" "https://asteraceae.cgrpoee.top/api/ping/"
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

Use this endpoint to check the public client IP address detected by the AGRP API service. For IP whitelist applications, use the IPv4 command below and send the returned IPv4 address to the AGRP team.

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

> **Note:** If this endpoint is opened directly in a browser, the detected address may be IPv6 because many networks prefer IPv6 automatically. For whitelist applications, please use `curl -4` from the actual server or computer that will access AGRP. A detected public IP address does not necessarily mean it is suitable for whitelist access. Campus networks, dormitory networks, public Wi-Fi, mobile hotspots, and personal broadband connections may use shared, dynamic, or temporary addresses. In these environments, please request an API key instead of IP whitelist access.

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
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/species/"
curl -4 -i "https://asteraceae.cgrpoee.top/api/files/genome/?species=Aann&type=lens"
curl -4 -L -o Aann.lens "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=lens"
```

<a id="sec_5_2"></a>

### 5.2 Annotation and Functional Genomics APIs

These endpoints query public annotation and functional genomics records. Use `limit` to avoid returning too many records at once.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genomics/interproscan/` | Query InterProScan annotation data. | `species` required; optional `database`, `q`, `limit`, `offset`. |
| `GET` `/api/genomics/kegg/` | Query KEGG annotation data. | `species` required; optional `q`, `limit`, `offset`. |
| `GET` `/api/genomics/regulatory-proteins/` | Query regulatory protein or transcription factor data. | Optional `species`, `type`, `q`, `limit`, `offset`. |
| `GET` `/api/genomics/m6a/` | Query m6A-related gene information. | Optional `species`, `first_class`, `hmm_id`, `limit`, `offset`. |
| `GET` `/api/genomics/duplication-types/` | Query duplication type data. | Optional `species`, `gene_id`, `limit`, `offset`. |

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/interproscan/?species=Aann&database=Pfam&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/regulatory-proteins/?species=Aann&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/m6a/?species=Aann&first_class=readers&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/duplication-types/?species=Aann&limit=5"
```

<a id="sec_5_3"></a>

### 5.3 Transposable Elements APIs

These endpoints list species with available transposable element resources and query TE records for a selected species.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genomics/transposable-elements/species/` | List species with available TE JSON resources. | None |
| `GET` `/api/genomics/transposable-elements/` | Query TE records for one species. | `species` required; optional `q`, `limit`, `offset`. |

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/transposable-elements/species/"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/transposable-elements/?species=Artemisia_annua&limit=5"
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
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/ancestral-genomes/"
curl -4 -i "https://asteraceae.cgrpoee.top/api/files/ancestral/?dataset=AAKI&type=cds"
curl -4 -L -o AAKI.cds "https://asteraceae.cgrpoee.top/api/download/ancestral/?dataset=AAKI&type=cds"
```

<a id="sec_6_2"></a>

### 6.2 Collinearity and Dotplot Static JSON APIs

These endpoints query static JSON resources used by collinearity and dotplot pages.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genosyn/collinear-kaks/` | Query collinearity and Ka/Ks records. | Optional `q`, `limit`, `offset`. |
| `GET` `/api/genosyn/dotplots/` | Query dotplot records. | Optional `q`, `limit`, `offset`. |

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/collinear-kaks/?q=Aann&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/dotplots/?q=Hean&limit=5"
```

<a id="sec_6_3"></a>

### 6.3 Geno-Syn Database Query APIs

These endpoints query database-backed comparative genomics resources. Some endpoints require a resource-specific parameter, such as `query_genome`.

The `block-details` endpoint returns block-level records for the selected `query_genome`. Use `gene_id` or `block_id` only when you want to narrow the result to a known exact identifier.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/genosyn/blocks/` | Query Aster-Blocks summary data. | `query_genome` required; optional `reference_genome`, `limit`, `offset`. |
| `GET` `/api/genosyn/block-details/` | Query block-level gene details. | `query_genome` required; optional `gene_id`, `block_id`, `limit`, `offset`. |
| `GET` `/api/genosyn/hierarchical-alignments/` | Query hierarchical multiple genome alignment data. | Optional `reference`, `q`, `limit`, `offset`. Example references: `Hean`, `Eupl`, `Vivi`, `Lssa`. |
| `GET` `/api/genosyn/hierarchical-genes/` | Query hierarchical gene data. | Optional `reference`, `species`, `gene_id`, `limit`, `offset`. |
| `GET` `/api/genosyn/evogenes/` | Query Aster-Evogenes data. | Optional `gene_id`, `species`, `function`, `limit`, `offset`. |
| `GET` `/api/genosyn/orthologous/` | Query orthologous gene data. | Optional `gene_id`, `orthogroup`, `species`, `limit`, `offset`. |
| `GET` `/api/genosyn/gene-families/` | Query gene family data. | Optional `gene_id`, `species`, `family`, `limit`, `offset`. |
| `GET` `/api/genosyn/rubber-genes/` | Query rubber biosynthesis gene data. | Optional `gene_id`, `species`, `function`, `limit`, `offset`. |
| `GET` `/api/genosyn/inulin-genes/` | Query inulin metabolism gene data. | Optional `gene_id`, `species`, `function`, `limit`, `offset`. |

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/blocks/?query_genome=Aann&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/block-details/?query_genome=Aann&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/hierarchical-alignments/?reference=Hean&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/hierarchical-genes/?reference=Hean&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/evogenes/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/orthologous/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/gene-families/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/rubber-genes/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/inulin-genes/?limit=5"
```

<a id="sec_7"></a>

## 7. Multi-Omics APIs

Multi-Omics APIs provide access to pan-genome, transcriptome, expression, and metabolomics resources.

| Endpoint | Purpose | Parameters |
| --- | --- | --- |
| `GET` `/api/multiomics/pangenome/` | Query pan-genome records. | Optional `q`, `limit`, `offset`. |
| `GET` `/api/multiomics/transcriptome/samples/` | List available transcriptome sample JSON files. | Optional `q`, `limit`, `offset`. |
| `GET` `/api/multiomics/transcriptome/sample/` | Read one transcriptome sample JSON file. | `filename` required. |
| `GET` `/api/multiomics/transcriptome/expression/` | Query transcriptome expression data. | `species` required; optional `gene_id`, `expression_index`, `limit`, `offset`. |
| `GET` `/api/multiomics/metabolomics/plant/` | Query plant metabolomics records. | Optional `cid`, `q`, `limit`, `offset`. |
| `GET` `/api/multiomics/metabolomics/scent/` | Query scent metabolomics records. | Optional `cid`, `q`, `limit`, `offset`. |

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/pangenome/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/samples/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/sample/?filename=Dapi_white%20petal.json"
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/expression/?species=Aann&expression_index=TPM&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/metabolomics/plant/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/metabolomics/scent/?limit=5"
```

<a id="sec_8"></a>

## 8. Rate Limits and Fair Use

The AGRP API provides public read-only access to selected Asteraceae genomic, comparative genomics, and multi-omics resources. Authentication is not required for standard query and download endpoints.

To maintain stable service for all users, API requests are rate-limited by client access level. Standard public users are limited by IP address. Authorized collaborators may receive higher quotas through registered IP addresses or dedicated API keys.

### Current public limits

| Endpoint group | Current public limit | Notes |
| --- | --- | --- |
| `/api/download/` | 5 requests per minute per IP; up to 2 concurrent download requests per IP. | Applies to genome and ancestral genome file downloads. |
| `/api/files/` | 60 requests per minute per IP. | Applies to file availability checks and file metadata endpoints. |
| `/api/genomics/`, `/api/genosyn/`, `/api/multiomics/` | 120 requests per minute per IP. | Applies to public JSON and database query endpoints. |
| `/api/ping/` | 60 requests per minute per IP. | Applies to the API health check endpoint. |
| `limit` parameter | Default: 20 records; maximum: 100 records per request. | Large values such as `limit=999999` are automatically capped at 100 for public access. |

### Authorized high-throughput access

For large-scale batch access, authorized collaborators may be granted higher quotas by registering a fixed IP address or by using a dedicated API key. The API endpoints remain the same; authorized requests simply receive a higher access tier.

| Access type | How it works | Typical use case |
| --- | --- | --- |
| Registered IP address | The collaborator provides a fixed server IPv4 address or stable institutional server network range, and AGRP grants higher quota for requests from that address. Personal computers on campus networks, dormitory networks, public Wi-Fi, mobile hotspots, or dynamic home broadband are generally not suitable for IP whitelist access. | Laboratory servers, institutional servers, or stable computing clusters. |
| Dedicated API key | The collaborator sends a key in the `X-AGRP-API-Key` request header. API keys should not be placed in the URL query string. | Teams without a fixed IP address, cross-institution workflows, or temporary authorized access. |
| Bulk package or manifest | For very large downloads, a curated package or file manifest may be more appropriate than sending many individual API requests. | Full dataset mirroring, long-term local analysis, or large-scale automated pipelines. |

### Checking the IP address for whitelist applications

Before requesting IP whitelist access, run the following command from the actual fixed server that will access AGRP. This command forces IPv4 and avoids accidentally submitting an IPv6 address returned by a browser request.

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"
```

> **Note:** The returned `detected_ip` is the client IP detected by AGRP for that request. However, a detected public IP is not always suitable for whitelist access. If the request comes from a campus network, dormitory network, public Wi-Fi, mobile hotspot, or personal dynamic broadband connection, use an AGRP API key instead.

### Using an API key

If the AGRP team provides an API key, include it in the HTTP request header named `X-AGRP-API-Key`. Do not include the key in a URL parameter, browser address bar, or shared link.

```bash
curl -4 -H "X-AGRP-API-Key: agrp_your_api_key_here" \
  "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=1000"

curl -4 -H "X-AGRP-API-Key: agrp_your_api_key_here" \
  -L -o Aann.cds \
  "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

> **Note:** If a request exceeds the current rate limit, the API returns `429 Too Many Requests`. Please wait briefly and retry with a lower request frequency. For repeated batch downloads or large automated workflows, contact the AGRP team for high-throughput access instead of sending high-frequency public requests.

### Recommended access pattern

- Check file availability before downloading large files.
- Use `limit` and `offset` for large tables instead of requesting all records at once.
- Avoid opening many parallel download connections from the same IP address.
- Use the `X-AGRP-API-Key` header only when an API key has been issued by the AGRP team.
- For full-dataset access, request a bulk package or manifest when possible.

<a id="sec_9"></a>

## 9. Error Responses

When a request is invalid or the requested resource does not exist, the API returns a JSON error response with an appropriate HTTP status code.

| Status | Meaning | Common cause |
| --- | --- | --- |
| `200` | OK | The request succeeded. |
| `400` | Bad Request | Missing required parameter, invalid file type, or unsafe parameter value. |
| `404` | Not Found | The requested file, species, dataset, or record does not exist. |
| `429` | Too Many Requests | The request exceeded the current IP-based rate limit or download concurrency limit. |

### 9.1 Missing required parameter

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/blocks/?limit=5"
```

```json
{
  "status": "error",
  "message": "Missing required parameter: query_genome"
}
```

Correct request:

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/blocks/?query_genome=Aann&limit=5"
```

### 9.2 Invalid file type

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=abc"
```

```json
{
  "status": "error",
  "message": "Invalid type parameter.",
  "type": "abc",
  "allowed_types": ["cds", "pep", "lens", "gff"]
}
```

### 9.3 File not found

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/download/genome/?species=NotExist&type=cds"
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

### 9.4 Invalid species parameter

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/download/genome/?species=../../etc/passwd&type=cds"
```

```json
{
  "status": "error",
  "message": "Invalid species parameter. Only letters, numbers, underscores, hyphens and dots are allowed.",
  "species": "../../etc/passwd"
}
```

### 9.5 Too many requests

If the request frequency or the number of concurrent downloads is too high, the API may return `429 Too Many Requests`.

```json
{
  "detail": "Request was throttled. Expected available in 42 seconds."
}
```

For concurrent download limits, the response may look like this:

```json
{
  "detail": "Too many concurrent download requests. Please wait for your current downloads to finish."
}
```

<a id="sec_10"></a>

## 10. Usage Examples

The examples below show common ways to use the API. The tables above provide the full list of endpoints and supported parameters.

### 10.1 Check your detected IPv4 address

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"
```

### 10.2 Check whether the API is available

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/ping/"
```

### 10.3 List genome resources and download a file

```bash
# List species with available genome files
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/species/"

# Check whether a specific file exists
curl -4 -i "https://asteraceae.cgrpoee.top/api/files/genome/?species=Aann&type=cds"

# Download the file
curl -4 -L -o Aann.cds "https://asteraceae.cgrpoee.top/api/download/genome/?species=Aann&type=cds"
```

### 10.4 Query annotation records

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/kegg/?species=Aann&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genomics/interproscan/?species=Aann&database=Pfam&limit=5"
```

### 10.5 Query Geno-Syn records

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/blocks/?query_genome=Aann&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/block-details/?query_genome=Aann&limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/genosyn/hierarchical-genes/?reference=Hean&limit=5"
```

### 10.6 Query Multi-Omics records

```bash
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/pangenome/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/samples/?limit=5"
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/transcriptome/sample/?filename=Dapi_white%20petal.json"
curl -4 -i "https://asteraceae.cgrpoee.top/api/multiomics/metabolomics/plant/?limit=5"
```

<a id="sec_11"></a>

## 11. Notes

- The API provides public read-only access to selected AGRP resources.
- Download endpoints return file streams only when the requested file exists. For scripts, check file availability before downloading large files.
- API requests may be rate-limited by IP address or authorized access level to maintain stable public service.
- Authorized collaborators may receive higher quotas through registered fixed server IPv4 addresses or the `X-AGRP-API-Key` request header.
- Use `curl -4 -i "https://asteraceae.cgrpoee.top/api/whoami/"` to check the IPv4 address detected by AGRP before requesting IP whitelist access.
- Use `limit` and `offset` when querying large tables or JSON resources. The default limit is 20. For public access, the maximum allowed limit is 100; authorized API-key users may have higher limit caps.
- URL-encode filenames or query values that contain spaces, for example `Dapi_white%20petal.json`.
- A successful response with an empty `data` list means the request was valid but no matching records were found.
- This documentation describes programmatic access to public resources and does not replace the normal website pages.
