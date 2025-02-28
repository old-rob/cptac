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

from cptac.cancers.source import Source
from cptac.tools.dataframe_tools import *
from cptac.exceptions import InvalidDataVersionError

class AwgBrca(Source):

    def __init__(self, version="latest", no_internet=False):
        """Load all of the awgbrca dataframes as values in the self._data dict variable, with names as keys, and format them properly.

        Parameters:
        version (str, optional): The version number to load, or the string "latest" to just load the latest building. Default is "latest".
        no_internet (bool, optional): Whether to skip the index update step because it requires an internet connection. This will be skipped automatically if there is no internet at all, but you may want to manually skip it if you have a spotty internet connection. Default is False.
        """

        # Set some needed variables, and pass them to the parent Dataset class __init__ function

        self.valid_versions = ["3.1", "3.1.1", "5.4"] # This keeps a record of all versions that the code is equipped to handle. That way, if there's a new data release but they didn't update their package, it won't try to parse the new data version it isn't equipped to handle.

        if version == "latest":
            version = sorted(self.valid_versions)[-1]

        self.data_files = {
            "3.1": {
                "acetylproteomics"  : "prosp-brca-v3.1-acetylome-ratio-norm-NArm.gct.gz",
                "CNV"               : "prosp-brca-v3.1-gene-level-cnv-gistic2-all_data_by_genes.gct.gz",
                "phosphoproteomics" : "prosp-brca-v3.1-phosphoproteome-ratio-norm-NArm.gct.gz",
                "proteomics"        : "prosp-brca-v3.1-proteome-ratio-norm-NArm.gct.gz",
                "transcriptomics"   : "prosp-brca-v3.1-rnaseq-fpkm-log2-row-norm-2comp.gct.gz",
                "annotation"        : "prosp-brca-v3.1-sample-annotation.csv.gz" },
            "3.1.1": {
                "followup"          : "Breast_One_Year_Clinical_Data_20160927.xls",
                "somatic_mutation"  : "prosp-brca-v3.0-v1.4.somatic.variants.070918.maf.gz",
                "acetylproteomics"  : "prosp-brca-v3.1-acetylome-ratio-norm-NArm.gct.gz",
                "CNV"               : "prosp-brca-v3.1-gene-level-cnv-gistic2-all_data_by_genes.gct.gz",
                "phosphoproteomics" : "prosp-brca-v3.1-phosphoproteome-ratio-norm-NArm.gct.gz",
                "proteomics"        : "prosp-brca-v3.1-proteome-ratio-norm-NArm.gct.gz",
                "transcriptomics"   : "prosp-brca-v3.1-rnaseq-fpkm-log2-row-norm-2comp.gct.gz",
                "annotation"        : "prosp-brca-v3.1-sample-annotation.csv.gz" },
            "5.4" : {
                "somatic_mutation"  : "prosp-brca-v3.0-v1.4.somatic.variants.070918.maf.gz",
                "acetylproteomics"  : "prosp-brca-v5.4-public-acetylome-ratio-norm-NArm.gct.gz", 
                "CNV"               : "prosp-brca-v5.4-public-gene-level-cnv-gistic2-all_data_by_genes.gct.gz", 
                #"not_used"         : "prosp-brca-v5.4-public-immune-profiling-scores-combined.gct.gz", 
                "phosphoproteomics" : "prosp-brca-v5.4-public-phosphoproteome-ratio-norm-NArm.gct.gz", 
                "proteomics"        : "prosp-brca-v5.4-public-proteome-ratio-norm-NArm.gct.gz", 
                #"not_used"         : "prosp-brca-v5.4-public-rnaseq-fpkm-log2-row-norm-median-mad.gct.gz", 
                "transcriptomics"   : "prosp-brca-v5.4-public-rnaseq-fpkm-log2.gct.gz",
                "annotation"        : "prosp-brca-v5.4-public-sample-annotation.csv.gz" }
        }

        self.load_functions = {
            'acetylproteomics'  : self.load_acetylproteomics,
            'clinical'          : self.load_annotations,
            'CNV'               : self.load_CNV,
            'derived_molecular' : self.load_annotations,
            'phosphoproteomics' : self.load_phosphoproteomics,
            'proteomics'        : self.load_proteomics,
            'transcriptomics'   : self.load_transcriptomics,
        }

        if version != "3.1":
            self.load_functions["somatic_mutation"] = self.load_somatic_mutation
        if version == "3.1.1":
            self.load_functions["followup"] = self.load_followup

        super().__init__(cancer_type="brca", source='awg', version=version, valid_versions=self.valid_versions, data_files=self.data_files, load_functions=self.load_functions, no_internet=no_internet)

    def how_to_cite(self):
        return super().how_to_cite(cancer_type='breast cancer', pmid=33212010)

    def load_annotations(self):
        df_type = 'annotation'
        # check to see if any of the specific annotation df's for awgbrca are not loaded
        if 'clinical' not in self._data or 'derived_molecular' not in self._data:
            # verify the df_type is valid for the current version and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)

            file_name = file_path.split(os.sep)[-1]

            if file_name == "prosp-brca-v3.1-sample-annotation.csv.gz":
                df = pd.read_csv(file_path, index_col=0)
                df = df.drop(columns="Participant") # This column is just a duplicate of the index
                df = df.rename(columns={"Sample.IDs": "Replicate_Measurement_IDs", "Type": "Sample_Tumor_Normal"})
                df = df.replace("unknown", np.nan)
                df = df.astype({"Age.in.Month": np.float64})
                df.index.name = "Patient_ID"
                
                # Separate the clinical and derived_molecular dataframes
                clinical = df[[
                     "Replicate_Measurement_IDs", "Sample_Tumor_Normal", "Age.in.Month", "Gender", "Race", "Human.Readable.Label", "Experiment", "Channel", "Stage", 
                     "PAM50", "NMF.v2.1", "ER", "PR", "ER.IHC.Score", "PR.IHC.Score", "Coring.or.Excision", "Ischemia.Time.in.Minutes", 
                     "Ischemia.Decade", "Necrosis", "Tumor.Cellularity", "Total.Cellularity", "In.CR", "QC.status"]]
                self.save_df("clinical", clinical)

                derived_molecular = df[[
                    "HER2.IHC.Score", "HER2.FISH.Status", "HER2.original", "HER2.Amplified", "HER2.refined", "STARD3.ERBB2.GRB7.protein", 
                    "HER2.class.Satpathy", "HER2.status.Satpathy", "PAM50.Her2.CNA", "PAM50.Her2.HER2.status", "CDH1.mutation", 
                    "GATA3.mutation", "MAP3K1.mutation", "PIK3CA.mutation", "PTEN.mutation", "TP53.mutation", "CDH1.mutation.status", 
                    "GATA3.mutation.status", "MAP3K1.mutation.status", "PIK3CA.mutation.status", "PTEN.mutation.status", "TP53.mutation.status", 
                    "Number.of.Mutations", "Number.of.Mutated.Genes", "Chromosome.INstability.index.CIN.", "ESTIMATE.TumorPurity", 
                    "ESTIMATE.ImmuneScore", "ESTIMATE.StromalScore", "xCell.ImmuneScore", "xCell.StromaScore", "Cibersort.Absolute.score", "Stemness.Score"]]
                self.save_df("derived_molecular", derived_molecular)
                
            elif file_name == "prosp-brca-v5.4-public-sample-annotation.csv.gz":
                df = pd.read_csv(file_path, index_col=0)
                df = df.rename(columns={"Sample.IDs": "Replicate_Measurement_IDs", "Tumor.Stage": "Stage"})
                #Note: The information here is the same as before, but the column has a different name. Anyone trying to get this information will have a hard time unless we rename it
                #Or at least make it known in the update notes that there has been a change and let people know about it
                df = df.replace("unknown", np.nan)
                df = df.astype({"Age.in.Month": np.float64})
                df.index.name = "Patient_ID"
                
                #Add tissue type column because it doesn't exist, all tissue should be cancer
                df["Sample_Tumor_Normal"] = "Tumor"
                
                clinical = df[['Replicate_Measurement_IDs', 'Sample_Tumor_Normal', 'TMT.Plex', 'TMT.Channel', 
                   'Stage', 'Ischemia.Time.in.Minutes', 'PAM50', 'NMF.Cluster',
                   'NMF.Cluster.Membership.Score', 'Age.in.Month', 'Gender', 'Ethnicity',
                   'ER.Updated.Clinical.Status', 'PR.Clinical.Status',
                   'ERBB2.Updated.Clinical.Status', 'TNBC.Updated.Clinical.Status',
                   'ERBB2.Proteogenomic.Status', 'TOP2A.Proteogenomic.Status']]
                self.save_df("clinical", clinical)
                
                derived_molecular = df[[
                   'ERBB2.Gene.Amplified', 'TOP2A.Gene.Amplified', 'ESTIMATE.TumorPurity', 'CIBERSORT.Absolute.Score', 'ESTIMATE.Immune.Score',
                   'xCell.Immune.Score', 'ESTIMATE.Stromal.Score', 'xCell.Stromal.Score', 'CD3.TILS.Status', 'CD3.TILS.Counts',
                   'Number.of.non.synonymous.Mutations', 'APOBEC.Signature', 'Chromosome.INstability.index.CIN.', 'Stemness.Score', 'TP53.Mutation.Type', 'PIK3CA.Mutation.Type',
                   'PTEN.Mutation.Type', 'MAP3K1.Mutation.Type', 'AKT1.Mutation.Type', 'GATA3.Mutation.Type', 'CBFB.Mutation.Type', 'KMT2C.Mutation.Type', 'SF3B1.Mutation.Type',
                   'ARID1A.Mutation.Type', 'MLLT4.Mutation.Type', 'TP53.Mutation.Status', 'PIK3CA.Mutation.Status', 'PTEN.Mutation.Status',
                   'MAP3K1.Mutation.Status', 'AKT1.Mutation.Status', 'GATA3.Mutation.Status', 'CBFB.Mutation.Status',
                   'KMT2C.Mutation.Status', 'SF3B1.Mutation.Status', 'ARID1A.Mutation.Status', 'MLLT4.Mutation.Status']]
                self.save_df("derived_molecular", derived_molecular)

    def load_acetylproteomics(self):
        df_type = 'acetylproteomics'
        if df_type not in self._data:
            # verify the df_type is valid for the current version and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)
            
            # process the file and add it to self._data
            df = pd.read_csv(file_path, sep='\t', skiprows=2, dtype=object) # First two rows of file aren't part of the dataframe. Also, due to extra metadata rows we're going to remove, all cols have mixed types, so we pass dtype=object for now.
            df = df[df["GeneSymbol"] != "na"] # There are several metadata rows at the beginning of the dataframe, which duplicate the clinical and derived_molecular dataframes. They all don't have a value for GeneSymbol, so we'll use that to filter them out.

            # Prepare some columns we'll need later for the multiindex
            df["variableSites"] = df["variableSites"].str.replace(r"[a-z\s]", "", regex=True) # Get rid of all lowercase delimeters and whitespace in the sites
            df = df.rename(columns={
                "GeneSymbol": "Name",
                "variableSites": "Site",
                "sequence": "Peptide", # We take this instead of sequenceVML, to match the other datasets' format
                "accession_numbers": "Database_ID" # We take all accession numbers they have, instead of the singular accession_number column
                })

            # Some rows have at least one localized acetylation site, but also have other acetylations that aren't localized. We'll drop those rows, if their localized sites are duplicated in another row, to avoid creating duplicates, because we only preserve information about the localized sites in a given row. However, if the localized sites aren't duplicated in another row, we'll keep the row.
            split_ids = df["id"].str.split('_', expand=True)
            unlocalized_to_drop = df.index[~split_ids[3].eq(split_ids[4]) & df.duplicated(["Name", "Site", "Peptide", "Database_ID"], keep=False)] # Column 3 of the split "id" column is number of phosphorylations detected, and column 4 is number of phosphorylations localized, so if the two values aren't equal, the row has at least one unlocalized site
            df = df.drop(index=unlocalized_to_drop)

            # Give it a multiindex
            df = df.set_index(["Name", "Site", "Peptide", "Database_ID"])                

            df = df.drop(columns=["id", "id.description", "geneSymbol", "numColumnsVMsiteObserved", "bestScore", "bestDeltaForwardReverseScore", 
            "Best_scoreVML", "sequenceVML", "accessionNumber_VMsites_numVMsitesPresent_numVMsitesLocalizedBest_earliestVMsiteAA_latestVMsiteAA",
            "protein_mw", "species", "speciesMulti", "orfCategory", "accession_number", "protein_group_num", "entry_name"]) # We don't need these. The dropped columns include a "geneSymbol" column that is a duplicate of the original GeneSymbol.
            df = df.apply(pd.to_numeric) # Now that we've dropped all the extra metadata columns, convert everything to floats.
            df = df.sort_index()
            df = df.transpose()
            df = df.sort_index()
            df.index.name = "Patient_ID"
            self.save_df(df_type, df)

    def load_CNV(self):
        df_type = 'CNV'
        if df_type not in self._data:
            # verify the df_type is valid for the current version and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)

            # parse the CNV data file
            df = pd.read_csv(file_path, sep='\t', skiprows=2, index_col=0, dtype=object) # First two rows of file aren't part of the dataframe. Also, due to extra metadata rows we're going to remove, all cols have mixed types, so we pass dtype=object for now.
            df = df[df["geneSymbol"] != "na"] # There are several metadata rows at the beginning of the dataframe, which duplicate the clinical and derived_molecular dataframes. They all don't have a value for geneSymbol, so we'll use that to filter them out.
            df = df.drop(columns="Cytoband")
            df["geneSymbol"] = df["geneSymbol"].str.rsplit('|', n=1, expand=True)[0] # Some of the geneSymbols have the gene IDs appended to them, to get rid of duplicates. We're going to create a multiindex with all the gene names and gene IDs, so we can drop the appended IDs.
            df = df.rename(columns={"geneSymbol": "Name", "Gene.ID": "Database_ID"})
            df = df.set_index(["Name", "Database_ID"])
            df = df.apply(pd.to_numeric) # Now that we've dropped all the extra metadata columns, convert everything to floats.
            df = df.sort_index()
            df = df.transpose()
            df = df.sort_index()
            df.index.name = "Patient_ID"
            self.save_df(df_type, df)
    
    def load_phosphoproteomics(self):
        df_type = 'phosphoproteomics'
        if df_type not in self._data:
            # perform initial checks and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)

            # load data file
            df = pd.read_csv(file_path, sep='\t', skiprows=2, dtype=object) # First two rows of file aren't part of the dataframe. Also, due to extra metadata rows we're going to remove, all cols have mixed types, so we pass dtype=object for now.
            df = df[df["GeneSymbol"] != "na"] # There are several metadata rows at the beginning of the dataframe, which duplicate the clinical and derived_molecular dataframes. They all don't have a value for GeneSymbol, so we'll use that to filter them out.

            # Prepare some columns we'll need later for the multiindex
            df["variableSites"] = df["variableSites"].str.replace(r"[a-z\s]", "", regex=True) # Get rid of all lowercase delimeters and whitespace in the sites
            df = df.rename(columns={
                "GeneSymbol": "Name",
                "variableSites": "Site",
                "sequence": "Peptide", # We take this instead of sequenceVML, to match the other datasets' format
                "accession_numbers": "Database_ID" # We take all accession numbers they have, instead of the singular accession_number column
                })

            # Some rows have at least one localized phosphorylation site, but also have other phosphorylations that aren't localized. We'll drop those rows, if their localized sites are duplicated in another row, to avoid creating duplicates, because we only preserve information about the localized sites in a given row. However, if the localized sites aren't duplicated in another row, we'll keep the row.
            split_ids = df["id"].str.split('_', expand=True)
            unlocalized_to_drop = df.index[~split_ids[3].eq(split_ids[4]) & df.duplicated(["Name", "Site", "Peptide", "Database_ID"], keep=False)] # Column 3 of the split "id" column is number of phosphorylations detected, and column 4 is number of phosphorylations localized, so if the two values aren't equal, the row has at least one unlocalized site
            df = df.drop(index=unlocalized_to_drop)

            # Give it a multiindex
            df = df.set_index(["Name", "Site", "Peptide", "Database_ID"])                

            df = df.drop(columns=["id", "id.description", "geneSymbol", "numColumnsVMsiteObserved", "bestScore", "bestDeltaForwardReverseScore",
            "Best_scoreVML", "Best_numActualVMSites_sty", "Best_numLocalizedVMsites_sty", "sequenceVML",
            "accessionNumber_VMsites_numVMsitesPresent_numVMsitesLocalizedBest_earliestVMsiteAA_latestVMsiteAA", "protein_mw", "species",
            "speciesMulti", "orfCategory", "accession_number", "protein_group_num", "entry_name"]) # We don't need these. The dropped columns include a "geneSymbol" column that is a duplicate of the original GeneSymbol.
            df = df.apply(pd.to_numeric) # Now that we've dropped all the extra metadata columns, convert everything to floats.
            df = df.sort_index()
            df = df.transpose()
            df = df.sort_index()
            df.index.name = "Patient_ID"
            self.save_df(df_type, df)

    def load_proteomics(self):
        df_type = 'proteomics'
        if df_type not in self._data:
            # perform initial checks and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)

            # load data file into df
            df = pd.read_csv(file_path, sep='\t', skiprows=2, dtype=object) # First two rows of file aren't part of the dataframe. Also, due to extra metadata rows we're going to remove, all cols have mixed types, so we pass dtype=object for now.
            df = df[df["GeneSymbol"] != "na"] # There are several metadata rows at the beginning of the dataframe, which duplicate the clinical and derived_molecular dataframes. They all don't have a value for GeneSymbol, so we'll use that to filter them out.

            # format df
            df = df.rename(columns={"GeneSymbol": "Name", "accession_numbers": "Database_ID"})
            df = df.set_index(["Name", "Database_ID"])
            df = df.drop(columns=["id", "id.description", "geneSymbol", "numColumnsProteinObserved", "numSpectraProteinObserved",
            "protein_mw", "percentCoverage", "numPepsUnique", "scoreUnique", "species", "orfCategory", "accession_number", 
            "subgroupNum", "entry_name"]) # We don't need these. The dropped columns include a "geneSymbol" column that is a duplicate of GeneSymbol.
            df = df.apply(pd.to_numeric) # Now that we've dropped all the extra metadata columns, convert everything to floats.
            df = df.sort_index()
            df = df.transpose()
            df = df.sort_index()
            df.index.name = "Patient_ID"
            self.save_df(df_type, df)

    def load_transcriptomics(self):
        df_type = 'transcriptomics'
        if df_type not in self._data:
            # verify the df_type is valid for the current version and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)

            # load file into df
            df = pd.read_csv(file_path, sep='\t', skiprows=2, index_col=0, dtype=object) # First two rows of file aren't part of the dataframe. Also, due to extra metadata rows we're going to remove, all cols have mixed types, so we pass dtype=object for now.
            df = df[df["geneSymbol"] != "na"] # There are several metadata rows at the beginning of the dataframe, which duplicate the clinical and derived_molecular dataframes. They all don't have a value for GeneSymbol, so we'll use that to filter them out.
            
            # format df
            df = df.set_index("geneSymbol")
            df = df.drop(columns="description") # We don't need this.
            df = df.apply(pd.to_numeric) # Now that we've dropped all the extra metadata columns, convert everything to floats.
            df = df.sort_index()
            df = df.transpose()
            df = df.sort_index()
            df.index.name = "Patient_ID"
            self.save_df(df_type, df)

    def load_followup(self):
        df_type = 'followup'
        if df_type not in self._data:
            # verify the df_type is valid for the current version and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)

            # load file into df
            df = pd.read_excel(file_path)

            # Replace redundant values for "not reported" with NaN
            nan_equivalents = ['Not Reported/ Unknown', 'Reported/ Unknown', 'Not Reported / Unknown', 'Not Reported /Unknown',
                'Not Applicable', 'not applicable', 'Not applicable;', 'na', 'Not Performed', 'Not Performed;',
                'Unknown tumor status', 'Unknown Tumor Status','Unknown', 'unknown', 'Not specified', 'Not Reported/ Unknown;']

            df = df.replace(nan_equivalents, np.nan)

            # Set and name the index
            df = df.rename(columns={"Participant ID": "Patient_ID"})
            df["Patient_ID"] = "X" + df["Patient_ID"]
            df = df.set_index("Patient_ID")
            df = df.sort_index()

            self.save_df(df_type, df)

    def load_somatic_mutation(self):
        df_type = 'somatic_mutation'
        if df_type not in self._data:
            # verify the df_type is valid for the current version and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)

            # load file into df
            df = pd.read_csv(file_path, sep='\t')
            
            # format df
            df = df.rename(columns={"Sample.ID": "Patient_ID"})
            df = df[['Patient_ID','Hugo_Symbol','Variant_Classification','HGVSp_Short']]
            df = df.rename(columns={
                "Hugo_Symbol":"Gene",
                "Variant_Classification":"Mutation",
                "HGVSp_Short":"Location"}) # Rename the columns we want to keep to the appropriate names
            df = df.sort_values(by=["Patient_ID", "Gene"])
            df = df.set_index("Patient_ID")

            self.save_df(df_type, df)