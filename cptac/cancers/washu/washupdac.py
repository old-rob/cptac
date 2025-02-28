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
import os
from gtfparse import read_gtf

from cptac.cancers.source import Source
from cptac.tools.dataframe_tools import *
from cptac.utils import get_boxnote_text
from cptac.cancers.mssm.mssm import Mssm


class WashuPdac(Source):

    def __init__(self, version="latest", no_internet=False):
        """Define which dataframes as are available in the self.load_functions dictionary variable, with names as keys.

        Parameters:
        version (str, optional): The version number to load, or the string "latest" to just load the latest building. Default is "latest".
        no_internet (bool, optional): Whether to skip the index update step because it requires an internet connection. This will be skipped automatically if there is no internet at all, but you may want to manually skip it if you have a spotty internet connection. Default is False.
        """
        
        # Set some needed variables, and pass them to the parent Dataset class __init__ function

        # This keeps a record of all versions that the code is equipped to handle. That way, if there's a new data release but they didn't update their package, it won't try to parse the new data version it isn't equipped to handle.
        self.valid_versions = ["1.0"]

        self.data_files = {
            "1.0": {
                "cibersort"         : "CIBERSORT.Output_Abs_PDA.txt",
                "CNV"               : "PDA.gene_level.from_seg.filtered.tsv",
                "mapping"           : "gencode.v22.annotation.gtf.gz",
                "miRNA"             : ["PDA_mature_miRNA_combined.tsv","PDA_precursor_miRNA_combined.tsv","PDA_total_miRNA_combined.tsv"],
                "readme"            : ["README_miRNA","README_CIBERSORT", "README_xCell","README_somatic_mutation_WXS","README_gene_expression","README.boxnote","README_ESTIMATE_WashU"],
                "somatic_mutation"  : "PDA_discovery.dnp.annotated.exonic.maf.gz",
                "transcriptomics"   : ["PDA_NAT_RNA-Seq_Expr_WashU_FPKM.tsv.gz","PDA_tumor_RNA-Seq_Expr_WashU_FPKM.tsv.gz"],
                "tumor_purity"      : "CPTAC_pancan_RNA_tumor_purity_ESTIMATE_WashU.tsv.gz",
                "xcell"             : "PDA_xCell.txt",
            }
        }

        #self._readme_files = {}

        self.load_functions = {
            'transcriptomics'   : self.load_transcriptomics,
            'somatic_mutation'  : self.load_somatic_mutation,
            'miRNA'             : self.load_miRNA,
            'xcell'             : self.load_xcell,
            'cibersort'         : self.load_cibersort,
            'CNV'               : self.load_CNV,
            'tumor_purity'      : self.load_tumor_purity,
            #'readme'            : self.load_readme,
        }

        if version == "latest":
            version = sorted(self.valid_versions)[-1]

        # Call the parent class __init__ function
        super().__init__(cancer_type="pdac", source='washu', version=version, valid_versions=self.valid_versions, data_files=self.data_files, load_functions=self.load_functions, no_internet=no_internet)

    def load_transcriptomics(self):
        df_type = 'transcriptomics'
        if df_type not in self._data:
            file_path_list = self.locate_files(df_type)
            # loop over list of file paths
            for file_path in file_path_list:
                path_elements = file_path.split(os.sep) # Get a list of the levels of the path
                file_name = path_elements[-1] # The last element will be the name of the file. We'll use this to identify files for parsing in the if/elif statements below
                    
                if file_name == "PDA_tumor_RNA-Seq_Expr_WashU_FPKM.tsv.gz":
                    df = pd.read_csv(file_path, sep='\t')
                    #change names to universal package names
                    df = df.rename(columns={"gene_name": "Name","gene_id": "Database_ID"})
                    df = df.set_index(["Name", "Database_ID"])
                    df = df.sort_index()
                    df = df.T #transpose 
                    df.index.name = "Patient_ID"
                    df.index = df.index.str.replace(r"-T", "", regex=True) #remove label for tumor samples
                    self._helper_tables["transcriptomics_tumor"] = df

                if file_name == "PDA_NAT_RNA-Seq_Expr_WashU_FPKM.tsv.gz":
                    df_norm = pd.read_csv(file_path, sep='\t')
                    #change names to universal package names
                    df_norm = df_norm.rename(columns={"gene_name": "Name","gene_id": "Database_ID"})  
                    df_norm = df_norm.set_index(["Name", "Database_ID"])
                    df_norm = df_norm.sort_index()
                    df_norm = df_norm.T #transpose
                    df_norm.index.name = "Patient_ID"
                    df_norm.index = df_norm.index.str.replace(r"-A", ".N", regex=True) #remove label for tumor samples
                    self._helper_tables["transcriptomics_normal"] = df_norm

            # combine and create transcriptomic dataframe            
            rna_tumor = self._helper_tables.get("transcriptomics_tumor")
            rna_normal = self._helper_tables.get("transcriptomics_normal") # Normal entries are already marked with 'N' on the end of the ID
            rna_combined = pd.concat([rna_tumor, rna_normal])
            # save df in self._data
            self.save_df(df_type, rna_combined)

    def load_somatic_mutation(self):
        df_type = 'somatic_mutation'
        if df_type not in self._data:
            file_path = self.locate_files(df_type)

            df = pd.read_csv(file_path, sep='\t')    
            # Rename the columns we want to keep to the appropriate names
            df = pd.read_csv(file_path, sep='\t')    
            df['Patient_ID'] = df.loc[:, 'Tumor_Sample_Barcode']
            df = df.rename(columns={
                        "Hugo_Symbol":"Gene",
                        "Gene":"Gene_Database_ID",
                        "Variant_Classification":"Mutation",
                        "HGVSp_Short":"Location"})

            df = df.set_index("Patient_ID")
            df = df[ ['Gene'] + ["Mutation"] + ["Location"] + [ col for col in df.columns if col not in ["Gene","Mutation","Location"] ] ]
            df.index = df.index.str.replace(r"_T", "", regex=True)     
            # save df in self._data
            self.save_df(df_type, df)

    def load_miRNA(self):
        self.load_precursor_miRNA()
        self.load_mature_miRNA()
        self.load_total_mRNA()

    def load_precursor_miRNA(self):
        df_type = 'precursor_miRNA'
        if df_type not in self._data:
            file_path = self.locate_files(df_type)

            df = pd.read_csv(file_path, delimiter = '\t', index_col = ['Name', 'ID','Alias'])
            df = df.transpose()
            df = average_replicates(df, common = '\.\d$') # average duplicates for C3L-02617 and C3N-02727
            df.index = df.index.str.replace('\.T$','', regex = True)
            df.index = df.index.str.replace('\.A$','.N', regex = True)
            df.index.name = 'Patient_ID'                
            # Sort
            normal = df.loc[df.index.str.contains('\.N$', regex =True)]
            normal = normal.sort_values(by=["Patient_ID"])
            tumor = df.loc[~ df.index.str.contains('\.N$', regex =True)]
            tumor = tumor.sort_values(by=["Patient_ID"])
            all_df = pd.concat([tumor, normal])
            # save df in self._data
            self.save_df(df_type, all_df)

    def load_mature_miRNA(self):
        df_type = 'mature_miRNA'
        if df_type not in self._data:
            file_path = self.locate_files(df_type)
            
            df = pd.read_csv(file_path, delimiter = '\t', index_col = ['Name', 'ID','Alias', 'Derives_from'])
            df = df.transpose()
            df = average_replicates(df, common = '\.\d$') # average duplicates for C3L-02617 and C3N-02727
            df.index = df.index.str.replace('\.T$','', regex = True)
            df.index = df.index.str.replace('\.A$','.N', regex = True)
            df.index.name = 'Patient_ID'                
            # Sort
            normal = df.loc[df.index.str.contains('\.N$', regex =True)]
            normal = normal.sort_values(by=["Patient_ID"])
            tumor = df.loc[~ df.index.str.contains('\.N$', regex =True)]
            tumor = tumor.sort_values(by=["Patient_ID"])
            all_df = pd.concat([tumor, normal])
            # save df in self._data
            self.save_df(df_type, all_df)
    
    def load_total_mRNA(self):
        df_type = 'total_miRNA'
        if df_type not in self._data:
            file_path = self.locate_files(df_type)
            
            df = pd.read_csv(file_path, delimiter = '\t', index_col = ['Name', 'ID','Alias'])
            df = df.transpose()
            df = average_replicates(df, common = '\.\d$') # average duplicates for C3L-02617 and C3N-02727
            df.index = df.index.str.replace('\.T$','', regex = True)
            df.index = df.index.str.replace('\.A$','.N', regex = True)
            df.index.name = 'Patient_ID'                
            # Sort
            normal = df.loc[df.index.str.contains('\.N$', regex =True)]
            normal = normal.sort_values(by=["Patient_ID"])
            tumor = df.loc[~ df.index.str.contains('\.N$', regex =True)]
            tumor = tumor.sort_values(by=["Patient_ID"])
            all_df = pd.concat([tumor, normal])
            # save df in self._data
            self.save_df(df_type, all_df)

    def load_xcell(self):
        df_type = 'xcell'
        if df_type not in self._data:
            file_path = self.locate_files(df_type)
        
            df = pd.read_csv(file_path, sep = '\t', index_col = 0) 
            df = df.transpose()
            df.columns.name = 'Name'
            df.index.name = 'Patient_ID'
            df.index = df.index.str.replace(r'-T$', '', regex=True) # remove label for tumor samples
            df.index = df.index.str.replace(r'-A$', '.N', regex=True) # change label for normal samples
            # save df in self._data
            self.save_df(df_type, df)

    def load_cibersort(self):
        df_type = 'cibersort'
        if df_type not in self._data:
            file_path = self.locate_files(df_type)

            df = pd.read_csv(file_path, sep = '\t', index_col = 0) 
            df.index.name = 'Patient_ID'
            df.columns.name = 'Name'
            df.index = df.index.str.replace(r'-T$', '', regex=True) 
            df.index = df.index.str.replace(r'-A$', '.N', regex=True)
            # save df in self._data
            self.save_df(df_type, df)

    def load_mapping(self):
        df_type = 'mapping'
        if "CNV_gene_ids" not in self._helper_tables:
            file_path = self.locate_files(df_type)

            df = read_gtf(file_path)
            df = df[["gene_name","gene_id"]]
            df = df.drop_duplicates()
            df = df.rename(columns={"gene_name": "Name","gene_id": "Database_ID"})
            df = df.set_index("Name")
            self._helper_tables["CNV_gene_ids"] = df

    def load_CNV(self):
        df_type = 'CNV'
        if df_type not in self._data:
            file_path = self.locate_files(df_type)

            df = pd.read_csv(file_path, sep="\t")
            df = df.rename(columns={"Gene": "Name"})
            df = df.set_index("Name")
            cnv = df

            self.load_mapping()
            gene_ids = self._helper_tables["CNV_gene_ids"]
            df = cnv.join(gene_ids,how = "left") #merge in gene_ids 
            df = df.reset_index()
            df = df.set_index(["Name", "Database_ID"]) #create multi-index
            df = df.T
            df.index.name = 'Patient_ID'
            # save df in self._data
            self.save_df(df_type, df)

    def load_tumor_purity(self):
        df_type = 'tumor_purity'
        if df_type not in self._data:
            file_path = self.locate_files(df_type)
        
            df = pd.read_csv(file_path, sep = "\t", na_values = 'NA')
            df.Sample_ID = df.Sample_ID.str.replace(r'-T', '', regex=True) # only tumor samples in file
            df = df.set_index('Sample_ID') 
            df.index.name = 'Patient_ID'

            # get clinical df (used to slice out cancer specific patient_IDs in tumor_purity file)
            mssmclin = Mssm(filter_type='pdac', version=self.version, no_internet=self.no_internet) #_get_version - pancandataset
            clinical_df = mssmclin.get_df('clinical')              
            patient_ids = clinical_df.index.to_list()
            df = df.loc[df.index.isin(patient_ids)]

            # save df in self._data
            self.save_df(df_type, df)

    # def load_readme(self):
    #     df_type = 'readme'
    #     if not self._readme_files:
    #         file_path_list = self.locate_files(df_type)
    #         # loop over list of file paths
    #         for file_path in file_path_list:
    #             path_elements = file_path.split(os.sep) # Get a list of the levels of the path
    #             file_name = path_elements[-1]# The last element will be the name of the file. We'll use this to identify files for parsing in the if/elif statements below

    #             if file_name == "README_miRNA":
    #                 with open(file_path, 'r') as reader:
    #                     self._readme_files["readme_miRNA"] = reader.read()
                        
    #             elif file_name == "README_CIBERSORT":
    #                 with open(file_path, 'r') as reader:
    #                     self._readme_files["readme_cibersort"] = reader.read()
                        
    #             elif file_name == "README_xCell":
    #                 with open(file_path, 'r') as reader:
    #                     self._readme_files["readme_xcell"] = reader.read()
                
    #             elif file_name == "README_somatic_mutation_WXS":
    #                 with open(file_path, 'r') as reader:
    #                     self._readme_files["readme_somatic_mutation"] = reader.read()
                        
    #             elif file_name == "README_gene_expression":
    #                 with open(file_path, 'r') as reader:
    #                     self._readme_files["readme_transcriptomics"] = reader.read()
                
    #             elif file_name == "README.boxnote":
    #                 self._readme_files["readme_cnv"] = get_boxnote_text(file_path)
                
    #             elif file_name == "README_ESTIMATE_WashU":
    #                 with open(file_path, 'r') as reader:
    #                     self._readme_files["readme_tumor_purity"] = reader.read()