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

import pandas as pd
import numpy as np
import os
import warnings
import datetime

from cptac.dataset import Dataset
from cptac.dataframe_tools import *
from cptac.exceptions import FailedReindexWarning, PublicationEmbargoWarning, ReindexMapError

class PdcHnscc(Dataset):

    def __init__(self, version="latest", no_internet=False):
        """Load all of the dataframes as values in the self._data dict variable, with names as keys, and format them properly.

        Parameters:
        version (str, optional): The version number to load, or the string "latest" to just load the latest building. Default is "latest".
        no_internet (bool, optional): Whether to skip the index update step because it requires an internet connection. This will be skipped automatically if there is no internet at all, but you may want to manually skip it if you have a spotty internet connection. Default is False.
        """

        # Set some needed variables, and pass them to the parent Dataset class __init__ function

        # This keeps a record of all versions that the code is equipped to handle. That way, if there's a new data release but they didn't update their package, it won't try to parse the new data version it isn't equipped to handle.
        valid_versions = ["1.0"]

        data_files = {
            "1.0": [
                "clinical.tsv.gz",
                "phosphoproteome.tsv.gz",
                "proteome.tsv.gz",
                "aliquot_to_patient_ID.tsv"
            ]
        }

        # Call the parent class __init__ function
        super().__init__(cancer_type="pdchnscc", version=version, valid_versions=valid_versions, data_files=data_files, no_internet=no_internet, attempt_update_index=False)

        # Load the data into dataframes in the self._data dict
        loading_msg = f"Loading {self.get_cancer_type()} v{self.version()}"
        for file_path in self._data_files_paths: # Loops through files variable

            # Print a loading message. We add a dot every time, so the user knows it's not frozen.
            loading_msg = loading_msg + "."
            print(loading_msg, end='\r')

            path_elements = file_path.split(os.sep) # Get a list of the levels of the path
            file_name = path_elements[-1] # The last element will be the name of the file. We'll use this to identify files for parsing in the if/elif statements below

            if file_name == "clinical.tsv.gz":
                df = pd.read_csv(file_path, sep="\t", index_col=0)
                clin_drop_rows = ['LungTumor1', 'LungTumor2', 'LungTumor3', 'QC1', 'QC2', 'QC3', 
                             'QC4', 'QC5', 'QC6', 'QC7', 'QC9', 'pooled sample']
                df = df.drop(clin_drop_rows, axis = 'index')
                self._data["clinical"] = df

            if file_name == "phosphoproteome.tsv.gz":
                df = pd.read_csv(file_path, sep="\t")
                df = df.set_index(["case_submitter_id"])
                self._data["phosphoproteomics"] = df

            if file_name == "proteome.tsv.gz":
                df = pd.read_csv(file_path, sep="\t", dtype={"case_submitter_id": "O"})
                self._data["proteomics"] = df
                
            elif file_name == "aliquot_to_patient_ID.tsv":
                df = pd.read_csv(file_path, sep = "\t")
                self._helper_tables["map_ids"] = df

                
        print(' ' * len(loading_msg), end='\r') # Erase the loading message
        formatting_msg = f"Formatting {self.get_cancer_type()} dataframes..."
        print(formatting_msg, end='\r')
        
        
        # Common rows to drop
        drop_rows = ['LungTumor1', 'LungTumor2', 'LungTumor3', 'QC1', 'QC2', 'QC3', 
                  'QC4', 'QC5', 'QC6', 'QC7', 'QC9']
         
        # Create dictionary with aliquot_ID as keys and patient_ID as values
        # aliquot_to_patient_ID.tsv contains only unique aliquots (no duplicates), 
        # so no need to slice out cancer specific aliquots
        mapping_df = self._helper_tables["map_ids"]
        matched_ids = {}
        for i, row in mapping_df.iterrows():
            matched_ids[row['aliquot_ID']] = row['patient_ID']

        # Proteomics
        prot = self._data["proteomics"]
        prot['Patient_ID'] = prot['aliquot_submitter_id'].replace(matched_ids) # aliquots to patient IDs
        prot = prot.set_index('Patient_ID')
        prot = prot.drop(['aliquot_submitter_id', 'case_submitter_id'], axis = 'columns')
        prot = prot.drop(drop_rows, axis = 'index') # drop quality control rows
        self._data["proteomics"] = prot
        
        # Phosphoproteomics
        phos = self._data["phosphoproteomics"]
        #import pdb;pdb.set_trace()
        phos['Patient_ID'] = phos['aliquot_submitter_id'].replace(matched_ids) # aliquots to patient IDs
        phos = phos.set_index('Patient_ID')
        phos = phos.drop(['aliquot_submitter_id', 'case_submitter_id'], axis = 'columns') # 3 duplicate aliquots and case 
        phos = phos.drop(drop_rows.append('pooled sample'), axis = 'index') # drop quality control rows
        phos = map_database_to_gene_pdc(phos, 'refseq') # Map refseq IDs to gene names
        self._data["phosphoproteomics"] = phos          
        
        
        self._data = sort_all_rows_pancan(self._data)  # Sort IDs (tumor first then normal)
        

        print(" " * len(formatting_msg), end='\r') # Erase the formatting message
