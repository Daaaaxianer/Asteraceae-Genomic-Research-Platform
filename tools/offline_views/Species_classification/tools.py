# -*- coding:utf-8 -*-
import os
import time
import traceback
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NCBI_EMAIL = "1457634627@qq.com"
NCBI_API_KEY = os.environ.get('NCBI_API_KEY', '')
NCBI_EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
HTTP_TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
RETRY_BASE_DELAY_SECONDS = 1
MAX_CONSECUTIVE_UPSTREAM_FAILURES = 3
USER_AGENT = f"AsteraceaeSpeciesClassification/1.0 ({NCBI_EMAIL})"


def retry_operation(func, *args, max_retries=MAX_RETRIES, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"   [Attempt {attempt + 1}/{max_retries}] Failed: {e} | Retrying...")
            if attempt == max_retries - 1:
                raise
            time.sleep((attempt + 1) * RETRY_BASE_DELAY_SECONDS)


def normalize_species_name(species_name):
    return species_name.lstrip("\ufeff").strip()


def fetch_ncbi_xml(endpoint, **params):
    query_params = dict(params)
    query_params.setdefault("email", NCBI_EMAIL)
    query_params.setdefault("api_key", NCBI_API_KEY)

    query_string = urlencode(query_params)
    request_url = f"{NCBI_EUTILS_BASE_URL}/{endpoint}?{query_string}"
    request = Request(request_url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return response.read()


def search_taxonomy_id(species_name):
    payload = retry_operation(
        fetch_ncbi_xml,
        "esearch.fcgi",
        db="taxonomy",
        term=species_name,
        retmode="xml",
        retmax=1,
    )
    root = ET.fromstring(payload)
    id_node = root.find("./IdList/Id")
    return id_node.text.strip() if id_node is not None and id_node.text else None


def fetch_taxonomy_lineage(tax_id):
    payload = retry_operation(
        fetch_ncbi_xml,
        "efetch.fcgi",
        db="taxonomy",
        id=tax_id,
        retmode="xml",
    )
    root = ET.fromstring(payload)
    lineage_node = root.find(".//Taxon/Lineage")
    return lineage_node.text.strip() if lineage_node is not None and lineage_node.text else ""


def get_taxonomy_info(species_name, output_file):
    clean_name = normalize_species_name(species_name)
    if not clean_name:
        return "empty"

    try:
        tax_id = search_taxonomy_id(clean_name)

        if not tax_id:
            output_file.write(f"{clean_name}\tNot Found\n")
            output_file.flush()
            print(f"Warning: {clean_name} not found in NCBI.")
            return "not_found"

        lineage = fetch_taxonomy_lineage(tax_id)
        output_file.write(f"{clean_name}\t{tax_id}\t{lineage}\n")
        output_file.flush()
        print(f"Success: {clean_name}")
        return "ok"

    except Exception as e:
        error_msg = str(e).replace("\n", " ")
        output_file.write(f"{clean_name}\tError: {error_msg}\n")
        output_file.flush()
        print(f"Error checking {clean_name}: {e}")
        return "error"


def species_classification_run_tools(place, base_dir=None):
    if not base_dir:
        base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "file_keep",
        )

    work_dir = os.path.join(base_dir, place)
    input_path = os.path.join(work_dir, "sp_list.txt")
    output_path = os.path.join(work_dir, "taxonomy_results.txt")

    print(f"--- Starting Classification Task: {place} ---")

    if not os.path.exists(input_path):
        print("Error: Input file sp_list.txt not found")
        return

    try:
        with open(output_path, "w", encoding="utf-8") as result_file:
            result_file.write("Species Name\tNCBI TaxID\tLineage\n")

            with open(input_path, "r", encoding="utf-8") as file_open:
                lines = [normalize_species_name(line) for line in file_open.readlines()]
                lines = [line for line in lines if line]
                total = len(lines)

                consecutive_failures = 0

                for index, plant_name in enumerate(lines):
                    status = get_taxonomy_info(plant_name, result_file)

                    if status == "error":
                        consecutive_failures += 1
                    elif status in ("ok", "not_found"):
                        consecutive_failures = 0

                    if index % 5 == 0 or index == total - 1:
                        print(f"Progress: {index + 1}/{total}")

                    if consecutive_failures >= MAX_CONSECUTIVE_UPSTREAM_FAILURES:
                        remaining = lines[index + 1:]
                        for remaining_name in remaining:
                            result_file.write(
                                f"{remaining_name}\tError: NCBI service unavailable or timed out repeatedly\n"
                            )
                        result_file.flush()
                        print("Warning: stopping early after repeated upstream failures.")
                        break

    except Exception as e:
        traceback.print_exc()
        with open(os.path.join(work_dir, "error_log.txt"), "w", encoding="utf-8") as err:
            err.write(str(e))

    print("--- Processing Complete ---")
