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


class UmichLscc(Dataset):

    def __init__(self, no_internet, version):
        """Load all of the umichlscc dataframes as values in the self._data dict variable, with names as keys, and format them properly.

        Parameters:
        version (str, optional): The version number to load, or the string "latest" to just load the latest building. Default is "latest".
        no_internet (bool, optional): Whether to skip the index update step because it requires an internet connection. This will be skipped automatically if there is no internet at all, but you may want to manually skip it if you have a spotty internet connection. Default is False.
        """

        # Set some needed variables, and pass them to the parent Dataset class __init__ function

        # This keeps a record of all versions that the code is equipped to handle. That way, if there's a new data release but they didn't update their package, it won't try to parse the new data version it isn't equipped to handle.
        valid_versions = ["1.0"]

        data_files = {
            "1.0": ["Report_abundance_groupby=protein_protNorm=MD_gu=2.tsv",
                    "aliquot_to_patient_ID.tsv",
                    "Report_abundance_groupby=multi-site_protNorm=MD_gu=2.tsv"
                #"S039_BCprospective_observed_0920.tsv.gz",
                #"S039_BCprospective_imputed_0920.tsv.gz"
            ]
        }

        # Call the parent class __init__ function
        super().__init__(cancer_type="umichlscc", version=version, valid_versions=valid_versions, data_files=data_files, no_internet=no_internet)

        # Load the data into dataframes in the self._data dict
        loading_msg = f"Loading {self.get_cancer_type()} v{self.version()}"
        for file_path in self._data_files_paths: # Loops through files variable

            # Print a loading message. We add a dot every time, so the user knows it's not frozen.
            loading_msg = loading_msg + "."
            print(loading_msg, end='\r')

            path_elements = file_path.split(os.sep) # Get a list of the levels of the path
            file_name = path_elements[-1] # The last element will be the name of the file. We'll use this to identify files for parsing in the if/elif statements below
            
            
            if file_name == "Report_abundance_groupby=protein_protNorm=MD_gu=2.tsv":
                df = pd.read_csv(file_path, sep = "\t") 
                df['Database_ID'] = df.Index.apply(lambda x: x.split('|')[0]) # Get protein identifier 
                df['Name'] = df.Index.apply(lambda x: x.split('|')[6]) # Get protein name 
                df = df.set_index(['Name', 'Database_ID']) # set multiindex
                df = df.drop(columns = ['Index', 'MaxPepProb', 'NumberPSM', 'Gene']) # drop unnecessary  columns
                df = df.transpose()
                ref_intensities = df.loc["ReferenceIntensity"] # Get reference intensities to use to calculate ratios 
                df = df.subtract(ref_intensities, axis="columns") # Subtract reference intensities from all the values
                df = df.iloc[1:,:] # drop ReferenceIntensity row 
                df.index.name = 'Patient_ID'

                # Drop quality control and ref intensity cols
                drop_cols = ['LUAD-Global-CR-pool1', 'LSCC-Tumor-ONLY-CR', 'JHU-HNSCC-CR',
                   'LUAD-Global-CR-pool-1', 'LSCC-Tumor-ONLY-CR.1', 'JHU-HNSCC-CR.1',
                   'LUAD-Global-CR-pool-2', 'JHU-HNSCC-CR.2', 'RefInt_LSCC-Global-CR',
                   'RefInt_LSCC-Global-CR.1', 'RefInt_LSCC-Global-CR.2',
                   'RefInt_LSCC-Global-CR.3', 'RefInt_LSCC-Global-CR.4',
                   'RefInt_LSCC-Global-CR.5', 'RefInt_LSCC-Global-CR.6',
                   'RefInt_LSCC-Global-CR.7', 'RefInt_LSCC-Global-CR.8',
                   'RefInt_LSCC-Global-CR.9', 'RefInt_LSCC-Global-CR.10',
                   'RefInt_LSCC-Global-CR.11', 'RefInt_LSCC-Global-CR.12',
                   'RefInt_LSCC-Global-CR.13', 'RefInt_LSCC-Global-CR.14',
                   'RefInt_LSCC-Global-CR.15', 'RefInt_LSCC-Global-CR.16',
                   'RefInt_LSCC-Global-CR.17', 'RefInt_LSCC-Global-CR.18',
                   'RefInt_LSCC-Global-CR.19', 'RefInt_LSCC-Global-CR.20',
                   'RefInt_LSCC-Global-CR.21']
                df = df.drop(drop_cols, axis = 'index')
                self._data["proteomics"] = df
            
            elif file_name == "aliquot_to_patient_ID.tsv":
                df = pd.read_csv(file_path, sep = "\t")
                self._helper_tables["map_ids"] = df
                
            elif file_name == "Report_abundance_groupby=multi-site_protNorm=MD_gu=2.tsv":
                df = pd.read_csv(file_path, sep = "\t") 
                # Parse a few columns out of the "Index" column that we'll need for our multiindex
                df[['Database_ID','Transcript_ID',"Gene_ID","Havana_gene","Havana_transcript","Transcript","Name","Site"]] = df.Index.str.split("\\|",expand=True)
                df[['num1','start',"end","detected_phos","localized_phos","Site"]] = df.Site.str.split("_",expand=True) 

                 # Some rows have at least one localized phosphorylation site, but also have other phosphorylations that aren't localized. We'll drop those rows, if their localized sites are duplicated in another row, to avoid creating duplicates, because we only preserve information about the localized sites in a given row. However, if the localized sites aren't duplicated in another row, we'll keep the row.
                unlocalized_to_drop = df.index[~df["detected_phos"].eq(df["localized_phos"]) & df.duplicated(["Name", "Site", "Peptide", "Database_ID"], keep=False)]# dectected_phos of the split "Index" column is number of phosphorylations detected, and localized_phos is number of phosphorylations localized, so if the two values aren't equal, the row has at least one unlocalized site
                df = df.drop(index=unlocalized_to_drop)

                df = df[df['Site'].notna()] # only keep columns with phospho site 
                df = df.set_index(['Name', 'Site', 'Peptide', 'Database_ID']) # This will create a multiindex from these columns, in this order.
                #drop columns not needed in df 
                df.drop([ 'Gene', "Index","num1","start","end","detected_phos","localized_phos","Havana_gene","Havana_transcript","MaxPepProb","Gene_ID","Transcript_ID","Transcript"], axis=1, inplace=True)
                self._data["phosphoproteomics"] = df


            '''
            if file_name == "S039_BCprospective_observed_0920.tsv.gz":
                df = pd.read_csv(file_path, sep="\t")
                df = df.transpose()
                df.index.name = 'Patient_ID'
                df.columns.name = 'Name'
                df = average_replicates(df)
                df = df.sort_values(by=["Patient_ID"])
                self._data["proteomics"] = df  
                
            if file_name == "S039_BCprospective_imputed_0920.tsv.gz":
                df = pd.read_csv(file_path, sep="\t")
                df = df.transpose()
                df.index.name = 'Patient_ID'
                df.columns.name = 'Name'
                df = average_replicates(df)
                df = df.sort_values(by=["Patient_ID"])
                self._data["proteomics_imputed"] = df'''
        
        
        print(' ' * len(loading_msg), end='\r') # Erase the loading message
        formatting_msg = f"Formatting {self.get_cancer_type()} dataframes..."
        print(formatting_msg, end='\r')
        
        # Get dictionary to map aliquot to patient IDs 
        # Create dictionary with aliquot_ID as keys and patient_ID as values
        mapping_df = self._helper_tables['map_ids']
        matched_ids = {}
        for i, row in mapping_df.iterrows():
            matched_ids[row['aliquot_ID']] = row['patient_ID']
            
        # Proteomics    
        prot = self._data["proteomics"]
        prot = prot.reset_index()
        prot = prot.replace(matched_ids) # replace aliquot_IDs with Patient_IDs
        prot = prot.set_index('Patient_ID')
        self._data["proteomics"] = prot
        
        # Phosphoproteomics 
        phos = self._data["phosphoproteomics"]
        phos = phos.rename(columns = matched_ids)# rename NAT ID columns with .N 
        phos = phos.T #transpose df 
        ref_intensities = phos.loc["ReferenceIntensity"]# Get reference intensities to use to calculate ratios 
        phos = phos.subtract(ref_intensities, axis="columns") # Subtract reference intensities from all the values, to get ratios
        phos = phos.iloc[1:,:] # drop ReferenceIntensity row 
        drop_cols_phos = ['LUAD-Global-CR-pool1','LSCC-Tumor-ONLY-CR','JHU-HNSCC-CR','LUAD-Global-CR-pool-1','LSCC-Tumor-ONLY-CR.1','JHU-HNSCC-CR.1','LUAD-Global-CR-pool-2','JHU-HNSCC-CR.2','RefInt_LSCC-Global-CR','RefInt_LSCC-Global-CR.1',
 'RefInt_LSCC-Global-CR.2','RefInt_LSCC-Global-CR.3','RefInt_LSCC-Global-CR.4','RefInt_LSCC-Global-CR.5',
 'RefInt_LSCC-Global-CR.6','RefInt_LSCC-Global-CR.7','RefInt_LSCC-Global-CR.8','RefInt_LSCC-Global-CR.9',
 'RefInt_LSCC-Global-CR.10','RefInt_LSCC-Global-CR.11','RefInt_LSCC-Global-CR.12', 'RefInt_LSCC-Global-CR.13',
 'RefInt_LSCC-Global-CR.14','RefInt_LSCC-Global-CR.15','RefInt_LSCC-Global-CR.16','RefInt_LSCC-Global-CR.17',
 'RefInt_LSCC-Global-CR.18','RefInt_LSCC-Global-CR.19','RefInt_LSCC-Global-CR.20','RefInt_LSCC-Global-CR.21']
          # Drop quality control and ref intensity cols
        phos = phos.drop(drop_cols_phos, axis = 'index')
        self._data["phosphoproteomics"] = phos
        
        
        self._data = sort_all_rows_pancan(self._data) # Sort IDs (tumor first then normal)
        

        print(" " * len(formatting_msg), end='\r') # Erase the formatting message
