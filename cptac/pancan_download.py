#   Copyright 2018 Samuel Payne sam_payne@byu.edu
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#       http://www.apache.org/licenses/LICENSE-2.0
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import os
from unittest.loader import VALID_MODULE_NAME
import pandas as pd
import requests
import warnings

import cptac
from cptac.file_download import get_box_token
from cptac.exceptions import CptacDevError, InvalidParameterError, NoInternetError, PdcDownloadError

from .brca import SOURCES as BRCA_SOURCES
from .ccrcc import SOURCES as CCRCC_SOURCES
from .coad import SOURCES as COAD_SOURCES
from .gbm import SOURCES as GBM_SOURCES
from .hnscc import SOURCES as HNSCC_SOURCES
from .lscc import SOURCES as LSCC_SOURCES
from .luad import SOURCES as LUAD_SOURCES
from .ov import SOURCES as OV_SOURCES
from .ucec import SOURCES as UCEC_SOURCES
from .pdac import SOURCES as PDAC_SOURCES

VALID_SOURCES = ['bcm', 'broad', 'mssm', 'pdc', 'umich', 'washu', 'harmonized']

STUDY_IDS_MAP = {
    "pdcbrca": {
        "acetylome": "PDC000239", # Prospective Breast BI Acetylome
        "phosphoproteome": "PDC000121", # Prospective BRCA Phosphoproteome S039-2
        "proteome": "PDC000120", # Prospective BRCA Proteome S039-1
    },
    "pdcccrcc": {
        "phosphoproteome": "PDC000128", # CPTAC CCRCC Discovery Study - Phosphoproteme S044-2
        "proteome": "PDC000127", # CPTAC CCRCC Discovery Study - Proteome S044-1
    },
    "pdccoad": {
        "phosphoproteome": "PDC000117", # Prospective COAD Phosphoproteome S037-3
        "proteome": "PDC000116", # Prospective COAD Proteome S037-2
    },
    "pdcgbm": {
        "acetylome": "PDC000245", # CPTAC GBM Discovery Study - Acetylome
        "phosphoproteome": "PDC000205", # CPTAC GBM Discovery Study - Phosphoproteome
        "proteome": "PDC000204", # CPTAC GBM Discovery Study - Proteome
    },
    "pdchnscc": {
        "phosphoproteome": "PDC000222", # CPTAC HNSCC Discovery Study - Phosphoproteome
        "proteome": "PDC000221", # CPTAC HNSCC Discovery Study - Proteome
    },
    "pdclscc": {
        "acetylome": "PDC000233", # CPTAC LSCC Discovery Study - Acetylome
        "phosphoproteome": "PDC000232", # CPTAC LSCC Discovery Study - Phosphoproteome
        "proteome": "PDC000234", # CPTAC LSCC Discovery Study - Proteome
        "ubiquitylome": "PDC000237", # CPTAC LSCC Discovery Study - Ubiquitylome
    },
    "pdcluad": {
        "acetylome": "PDC000224", # CPTAC LUAD Discovery Study - Acetylome
        "phosphoproteome": "PDC000149", # CPTAC LUAD Discovery Study - Phosphoproteome
        "proteome": "PDC000153", # CPTAC LUAD Discovery Study - Proteome
    },
    "pdcov": {
        "phosphoproteome": "PDC000119", # Prospective OV Phosphoproteome S038-3
        "proteome": "PDC000118", # Prospective OV Proteome S038-2
    },
    "pdcpdac": {
        "proteome": "PDC000270", # CPTAC PDAC Discovery Study - Proteome
        "phosphoproteome": "PDC000271", # CPTAC PDAC Discovery Study - Phosphoproteome
    },
    "pdcucec": {
        "acetylome": "PDC000226", # CPTAC UCEC Discovery Study - Acetylome
        "phosphoproteome": "PDC000126", # UCEC Discovery - Phosphoproteome S043-2
        "proteome": "PDC000125", # UCEC Discovery - Proteome S043-1
    },
}


def download(dataset, version="latest", redownload=False, box_token=None):

    if type(dataset) is str:

        dataset = dataset.lower()
        if dataset.startswith("pdc"):
            return _pdc_download(dataset, version=version, redownload=redownload, box_token=box_token)
        
        if dataset.startswith("pancan") or dataset == "all":
            download = _download_by_cancer
    
    elif type(dataset) is dict:
        download = _download_by_source

    else:
        raise InvalidParameterError(f"the dataset parameter must be a string of the cancer type (e.g. 'pancanbrca') or a dictionary {{'source' : datatype}} (e.g. {{'broad': 'CNV'}})")

    if box_token is None:
        box_token = get_box_token()

    return download(dataset, version, redownload, box_token)

def download_pdc_id(pdc_id, _download_msg=True):
    """Download a PDC dataset by its PDC study id.
    
    Returns:
    pandas.DataFrame: The clinical table for the study id.
    pandas.DataFrame: The quantitative table for the study id.
    """

    if _download_msg:
        clin_msg = f"Downloading clinical table for {pdc_id}..."
        print(clin_msg, end="\r")

    # Download the clinical table
    clin = _download_study_clin(pdc_id).\
    set_index("case_submitter_id").\
    sort_index()

    if _download_msg:
        print(" " * len(clin_msg), end="\r")
        bio_msg = f"Downloading biospecimenPerStudy table for {pdc_id}..."
        print(bio_msg, end="\r")

    # The the biospecimenPerStudy table, which has both patient IDs and aliquot IDs
    bio = _download_study_biospecimen(pdc_id).\
    set_index("aliquot_submitter_id").\
    sort_index()

    if _download_msg:
        print(" " * len(bio_msg), end="\r")
        quant_msg = f"Downloading quantitative table for {pdc_id}..."
        print(quant_msg, end="\r")

    # Get the quantitative data table
    quant = _download_study_quant(pdc_id)

    if _download_msg:
        print(" " * len(quant_msg), end="\r")
        format_msg = f"Formatting tables for {pdc_id}..."
        print(format_msg, end="\r")

    # Join the patient IDs from the biospecimenPerStudy table into the quant table
    quant = quant.\
    assign(aliquot_submitter_id=quant.iloc[:, 0].str.split(":", n=1, expand=True)[1]).\
    drop(columns=quant.columns[0]).\
    set_index("aliquot_submitter_id").\
    sort_index()

    quant = bio.\
    join(quant, how="inner").\
    reset_index().\
    set_index(["case_submitter_id", "aliquot_submitter_id"]).\
    sort_index()

    # Clear message
    if _download_msg:
        print(" " * len(format_msg), end="\r")

    return clin, quant

def list_pdc_datasets():
    for dataset in STUDY_IDS_MAP.keys():
        print(f"Pdc{dataset[3:].title()}:")
        for data_type in STUDY_IDS_MAP[dataset].keys():
            print(f"\t{data_type}: {STUDY_IDS_MAP[dataset][data_type]}")

# Helper functions
def _download_by_cancer(dataset, version, redownload, box_token):
    '''Download PDC data by cancer (brca, hnscc, etc.)
    '''
    if dataset.startswith("pancan") or dataset == "all":

        if dataset == "pancanbrca":
            sources = BRCA_SOURCES
        elif dataset == "pancanccrcc":
            sources = CCRCC_SOURCES
        elif dataset == "pancancoad":
            sources = COAD_SOURCES
        elif dataset == "pancangbm":
            sources = GBM_SOURCES
        elif dataset == "pancanhnscc":
            sources = HNSCC_SOURCES
        elif dataset == "pancanlscc":
            sources = LSCC_SOURCES
        elif dataset == "pancanluad":
            sources = LUAD_SOURCES
        elif dataset == "pancanov":
            sources = OV_SOURCES
        elif dataset == "pancanucec":
            sources = UCEC_SOURCES
        elif dataset == "pancanpdac":
            sources = PDAC_SOURCES
        elif dataset == "all":
            sources = sorted(set(BRCA_SOURCES + CCRCC_SOURCES + COAD_SOURCES + GBM_SOURCES + HNSCC_SOURCES + LSCC_SOURCES + LUAD_SOURCES + OV_SOURCES + UCEC_SOURCES + PDAC_SOURCES))
        else:
            raise InvalidParameterError(f"{dataset} is not a valid dataset.")

        overall_success = True
        for source in sources:

            if source.startswith("pdc"):
                single_success = download(source, version=version, redownload=redownload, box_token=box_token)
            else:
                single_success = cptac.download(source, version=version, redownload=redownload, _box_auth=True, _box_token=box_token)

            if not single_success:
                overall_success = False

        return overall_success

    else:
        return cptac.download(dataset, version=version, redownload=redownload, _box_auth=True, _box_token=box_token)

def _download_by_source(dataset, version, redownload, box_token):
    '''Download PDC data by source (broad, washu, etc.)
    dataset: a dict of form {datatype : source} or {source : datatype}
        datatype should be a string
        source can be a string or a list of strings
    '''
    # verify all sources are valid
    for source in dataset.keys():
        invalid_sources = set()
        if source.lower() not in VALID_SOURCES:
            invalid_sources.add(source)
            
        if len(invalid_sources) > 0:
            raise InvalidParameterError(f"Invalid source(s) detected: {invalid_sources}. Valid sources include {VALID_SOURCES}.")

    # all valid sources for all cancer types
    SOURCES = sorted(set(BRCA_SOURCES + CCRCC_SOURCES + COAD_SOURCES + GBM_SOURCES + HNSCC_SOURCES + LSCC_SOURCES + LUAD_SOURCES + OV_SOURCES + UCEC_SOURCES + PDAC_SOURCES))
    
    overall_success = True
    for source, datatype in dataset.items():

        if type(dataset) is not list:
            datatypes = list([datatype])
        
        if source.startswith("pdc"):
            warnings.warn(f"Individual pdc datatypes are unable to be downloaded individually. Downloading all datatypes...")
            single_success = download(source, version=version, redownload=redownload, box_token=box_token)
            if not single_success:
                overall_success = False
        else:
            # get data for all cancer types from the given source
            for s in SOURCES:
                if s.startswith(source):
                    single_success = cptac.download(dataset='all', source=source, datatypes=datatypes, version=version, redownload=redownload, _box_auth=True, _box_token=box_token)
                    if not single_success:
                        overall_success = False

    return overall_success
                
    
def _pdc_download(dataset, version, redownload, box_token):
    """Download data for the specified cancer type from the PDC."""

    dataset = str.lower(dataset)

    if dataset == "pdcall":
        overall_result = True
        for dataset in STUDY_IDS_MAP.keys():
            if not _pdc_download(dataset, version, redownload):
                overall_result = False

        return overall_result

    if not dataset.startswith("pdc"):
        raise InvalidParameterError(f"_pdc_download function can only be used for PDC datasets, which start with the prefix 'pdc'. You tried to download '{dataset}'.")

    if dataset not in STUDY_IDS_MAP.keys():
        raise InvalidParameterError(f"PDC dataset must be one of the following:\n{list(STUDY_IDS_MAP.keys())}\nYou passed '{dataset}'.")

    dataset_ids = STUDY_IDS_MAP[dataset]

    # Download the file for mapping aliquots to patient IDs
    if not cptac.download(dataset, version=version, redownload=redownload, _box_auth=True, _box_token=box_token):
        return False

    path_here = os.path.abspath(os.path.dirname(__file__))
    cancer_dir = os.path.join(path_here, f"data_{dataset}")

    # Check that the index file exists. If not, there was an uncaught error in the mapping file download.
    index_path = os.path.join(cancer_dir, "index.txt")
    if not os.path.isfile(index_path):
        raise CptacDevError(f"Index file not found at {index_path}. Mapping file download probably failed.")

    # See what data files we need to download
    data_dir = os.path.join(cancer_dir, f"{dataset}_v1.0")

    # If any of the files are missing, we're going to delete any remaining and redownload all, in case the missing files are a sign of a previous data problem
    data_files = [f"{data_type}.tsv.gz" for data_type in dataset_ids.keys()] + ["clinical.tsv.gz"]
    for data_file in data_files:
        data_file_path = os.path.join(data_dir, data_file)
        if not os.path.isfile(data_file_path):
            redownload = True
            break

    if redownload:
        for data_file in data_files:
            data_file_path = os.path.join(data_dir, data_file)
            if os.path.isfile(data_file_path):
                os.remove(data_file_path)
    else:
        return True # If all the files are there and the user didn't ask to redownload, we're done.

    # Now download all the data files

    # We'll combine all the clinical tables in case there are differences
    master_clin = pd.DataFrame()

    for data_type in dataset_ids.keys():

        # Print an update
        download_msg = f"Downloading {dataset} {data_type} files..."
        print(download_msg, end="\r")

        # Get the clinical and quantitative tables for the study ID
        clin, quant = download_pdc_id(dataset_ids[data_type], _download_msg=False)

        # Print a new update
        print(" " * len(download_msg), end="\r")
        save_msg = f"Saving {dataset} {data_type} files..."
        print(save_msg, end="\r")

        # Append the clinical dataframe
        #master_clin = master_clin.append(clin)
        master_clin = pd.concat([master_clin,clin], axis=0, join='outer')

        # Save the quantitative table
        quant.to_csv(os.path.join(data_dir, f"{data_type}.tsv.gz"), sep="\t")

        # Erase update
        print(" " * len(save_msg), end="\r")

    # Print an update
    save_msg = f"Saving {dataset} clinical file..."
    print(save_msg, end="\r")

    # Drop any duplicated rows in combined clinical table, then save it too
    master_clin = master_clin.drop_duplicates(keep="first")

    master_clin.to_csv(os.path.join(data_dir, "clinical.tsv.gz"), sep="\t")

    # Erase update
    print(" " * len(save_msg), end="\r")

    return True

def _download_study_clin(pdc_study_id):
    """Download PDC clinical data for a particular study."""

    clinical_query = '''
    query {
        clinicalPerStudy(pdc_study_id: "''' + pdc_study_id + '''", acceptDUA: true) {
            age_at_diagnosis, ajcc_clinical_m, ajcc_clinical_n, ajcc_clinical_stage, ajcc_clinical_t, ajcc_pathologic_m,
            ajcc_pathologic_n, ajcc_pathologic_stage, ajcc_pathologic_t, ann_arbor_b_symptoms, ann_arbor_clinical_stage,
            ann_arbor_extranodal_involvement, ann_arbor_pathologic_stage, best_overall_response, burkitt_lymphoma_clinical_variant,
            case_id, case_submitter_id, cause_of_death, circumferential_resection_margin, classification_of_tumor, colon_polyps_history,
            days_to_best_overall_response, days_to_birth, days_to_death, days_to_diagnosis, days_to_hiv_diagnosis, days_to_last_follow_up,
            days_to_last_known_disease_status, days_to_new_event, days_to_recurrence, demographic_id, demographic_submitter_id,
            diagnosis_id, diagnosis_submitter_id, disease_type, ethnicity, figo_stage, gender, hiv_positive, hpv_positive_type, hpv_status,
            icd_10_code, iss_stage, last_known_disease_status, laterality, ldh_level_at_diagnosis, ldh_normal_range_upper,
            lymphatic_invasion_present, lymph_nodes_positive, method_of_diagnosis, morphology, new_event_anatomic_site, new_event_type,
            overall_survival, perineural_invasion_present, primary_diagnosis, primary_site, prior_malignancy, prior_treatment,
            progression_free_survival, progression_free_survival_event, progression_or_recurrence, race, residual_disease,
            site_of_resection_or_biopsy, status, synchronous_malignancy, tissue_or_organ_of_origin, tumor_cell_content, tumor_grade,
            tumor_stage, vascular_invasion_present, vital_status, year_of_birth, year_of_death, year_of_diagnosis
        }
    }
    '''

    result_json = _query_pdc(clinical_query)
    result_df = pd.\
    DataFrame(result_json["data"]["clinicalPerStudy"])

    return result_df

def _download_study_biospecimen(pdc_study_id):
    """Download PDC biospecimen data for a particular study."""

    biospecimen_query = '''
    query {
        biospecimenPerStudy(pdc_study_id: "''' + pdc_study_id + '''", acceptDUA: true) {
            aliquot_submitter_id
            case_submitter_id
        }
    }
    '''

    result_json = _query_pdc(biospecimen_query)
    result_df = pd.\
    DataFrame(result_json["data"]["biospecimenPerStudy"])

    return result_df

def _download_study_quant(pdc_study_id):
    """Download PDC quantitative data for a particular study."""

    proteome_query = '''
    query {
        quantDataMatrix(pdc_study_id: "''' + pdc_study_id + '''", data_type: "log2_ratio", acceptDUA: true)
    }
    '''

    result_json = _query_pdc(proteome_query)
    result_df = pd.DataFrame(result_json["data"]["quantDataMatrix"])

    if result_df.shape[1] != 0:
        result_df = result_df.set_index(result_df.columns[0]).transpose()
    else:
        raise PdcDownloadError(f"quantDataMatrix table returned for PDC study ID {pdc_study_id} was empty.")

    return result_df

def _query_pdc(query):
    """Send a GraphQL query to the PDC and return the results."""

    url = 'https://pdc.cancer.gov/graphql'

    try:
        response = requests.post(url, json={'query': query})
        response.raise_for_status() # Raises a requests.HTTPError if the response code was unsuccessful

    except requests.RequestException: # Parent class for all exceptions in the requests module
        raise NoInternetError("Insufficient internet. Check your internet connection.") from None

    return response.json()

def _check_ids_match(ids_map):
    """Check that the ids in the download function's STUDY_IDS_MAP match up."""
    
    for cancer in ids_map.values():
        for data in cancer.values():
            pdc_study_id = data["pdc_study_id"]
            study_submitter_id = data["study_submitter_id"]

            query = '''
            query {
              study (pdc_study_id: "''' + pdc_study_id + '''" acceptDUA: true) {
                pdc_study_id,
                study_submitter_id
              }
            }
            '''

            idres = _query_pdc(query)

            server_psi = idres["data"]["study"][0]["pdc_study_id"]
            server_ssi = idres["data"]["study"][0]["study_submitter_id"]

            assert server_psi == pdc_study_id
            assert server_ssi == study_submitter_id

            print(f"{server_psi} == {pdc_study_id}")
            print(f"{server_ssi} == {study_submitter_id}")
            print()
