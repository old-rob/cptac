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

from cptac.cancers.source import Source
from cptac.tools.dataframe_tools import *
from cptac.exceptions import FailedReindexWarning, PublicationEmbargoWarning, ReindexMapError


class Mssm(Source):

    def __init__(self, filter_type, version="latest", no_internet=False):
        """Define which dataframes as are available in the self.load_functions dictionary variable, with names as keys.

        Parameters:
        version (str, optional): The version number to load, or the string "latest" to just load the latest datafreeze. Default is "latest".
        no_internet (bool, optional): Whether to skip the index update step because it requires an internet connection. This will be skipped automatically if there is no internet at all, but you may want to manually skip it if you have a spotty internet connection. Default is False.
        filter_type (str): The cancer type for which you want information. Mssm keeps all data in a single table, so to get data on a single cancer type all other types are filtered out.
        """

        # Set some needed variables, and pass them to the parent Dataset class __init__ function

        # This keeps a record of all versions that the code is equipped to handle. That way, if there's a new data release but they didn't update their package, it won't try to parse the new data version it isn't equipped to handle.
        self.valid_versions = ["1.0"]

        self.data_files = {
            "1.0": {
                "clinical" : "clinical_Pan-cancer.Dec2020.tsv"
            }
        }

        self.load_functions = {
            'clinical' : self.load_clinical,
        }

        if version == "latest":
            version = sorted(self.valid_versions)[-1]

        # Mssm is special in that it keeps information for all cancer types in a single table
        # We can still make this look like the other sources, but it works a little different under the hood
        # Essentially Mssm always loads the entire clinical table, then filters it based on filter_type

        # Call the parent class __init__ function, cancer_type is dynamic and based on whatever cancer is being filtered for
        super().__init__(cancer_type=filter_type, source='mssm', version=version, valid_versions=self.valid_versions, data_files=self.data_files, load_functions=self.load_functions, no_internet=no_internet)


    # This is all clinical data, but mssm will have other load functions to get only a subset of this data
    def load_clinical(self):
        df_type = 'clinical'

        if df_type not in self._data:
            # perform initial checks and get file path (defined in source.py, the parent class)
            file_path = self.locate_files(df_type)

            # which cancer_type goes with which cancer in the mssm table
            tumor_codes = {'brca':'BR', 'ccrcc':'CCRCC',
                           'ucec':'UCEC', 'gbm':'GBM', 'hnscc':'HNSCC',
                           'lscc':'LSCC', 'luad':'LUAD', 'pdac':'PDA',
                           'hcc':'HCC', 'coad':'CO', 'ov':'OV'}

            df = pd.read_csv(file_path, sep='\t')
            df = df.loc[df['tumor_code'] == tumor_codes[self.cancer_type]]
            df = df.loc[df['discovery_study'] != 'No'] # Only keep discovery study = 'Yes' or 'na'
            df = df.set_index("case_id")
            df.index.name = 'Patient_ID'
            df = df.sort_values(by=["Patient_ID"])

            self.save_df(df_type, df)

    # TODO: Add in the different tables below and give the user a way to access them

#             # Separate out demographic, previous_cancer, medical_conditions, cancer_diagnosis, and followup dfs
#             all_clinical = df
#             demographic_df = all_clinical[['discovery_study', 'discovery_study/type_of_analyzed_samples', 'consent/age',
#                               'consent/sex', 'consent/race', 'consent/ethnicity', 'consent/ethnicity_race_ancestry_identified',
#                               'consent/collection_in_us', 'consent/participant_country', 'consent/maternal_grandmother_country',
#                               'consent/maternal_grandfather_country', 'consent/paternal_grandmother_country',
#                               'consent/paternal_grandfather_country', 'consent/deaf_or_difficulty_hearing',
#                               'consent/blind_or_difficulty_seeing',
#                               'consent/difficulty_concentrating_remembering_or_making_decisions',
#                               'consent/difficulty_walking_or_climbing_stairs', 'consent/difficulty_dressing_or_bathing',
#                               'consent/difficulty_doing_errands', 'consent/consent_form_signed', 'consent/case_stopped',
#                               'medications/medication_name_vitamins_supplements', 'medications/history_source',
#                               'medical_history/height_at_time_of_surgery_cm', 'medical_history/weight_at_time_of_surgery_kg',
#                               'medical_history/bmi', 'medical_history/history_of_cancer', 'medical_history/alcohol_consumption',
#                               'medical_history/tobacco_smoking_history',
#                               'medical_history/age_at_which_the_participant_started_smoking',
#                               'medical_history/age_at_which_the_participant_stopped_smoking',
#                               'medical_history/on_the_days_participant_smoked_how_many_cigarettes_did_he_she_usually_smoke',
#                               'medical_history/number_of_pack_years_smoked',
#                               'medical_history/was_the_participant_exposed_to_secondhand_smoke',
#                               'medical_history/exposure_to_secondhand_smoke_in_household_during_participants_childhood',
#                               'medical_history/exposure_to_secondhand_smoke_in_participants_current_household', 'medical_history/number_of_years_participant_has_consumed_more_than_2_drinks_per_day_for_men_and_more_than_1_drink_per_day_for_women']]
#             self._data['demographic'] = demographic_df

#             # Create previous_cancer df (no data for HCC, BR, CO, OV)
#             previous_cancer_df = all_clinical[['cancer_history/cancer_type', 'cancer_history/history_source',
#                                             'cancer_history/history_of_any_treatment',
#                                             'cancer_history/medical_record_documentation_of_this_history_of_cancer_and_treatment']]
#             # include previous_cancer if it's not empty
#             previous_cancer_df = previous_cancer_df.dropna(how='all')
#             if len(previous_cancer_df.index) != 0:
#                 self._data['previous_cancer'] = previous_cancer_df

#             # Create medical_conditions df (no data for HCC, BR, CO, OV)
#             medical_conditions_df = all_clinical[['general_medical_history/medical_condition',
#                                              'general_medical_history/history_of_treatment',
#                                              'general_medical_history/history_source']]
#             # include medical_conditions if it's not empty
#             medical_conditions_df = medical_conditions_df.dropna(how='all')
#             if len(medical_conditions_df.index) != 0:
#                 self._data['medical_conditions'] = medical_conditions_df

#             # Create cancer_diagnosis df
#             cancer_diagnosis_df = all_clinical[['baseline/tumor_site', 'baseline/tumor_site_other', 'baseline/tumor_laterality',
#                                    'baseline/tumor_focality', 'baseline/tumor_size_cm', 'baseline/histologic_type',
#                                    'cptac_path/histologic_grade', 'baseline/tumor_necrosis', 'baseline/margin_status',
#                                    'baseline/ajcc_tnm_cancer_staging_edition', 'baseline/pathologic_staging_primary_tumor',
#                                    'baseline/pathologic_staging_regional_lymph_nodes', 'baseline/number_of_lymph_nodes_examined',
#                                    'baseline/ihc_staining_done', 'baseline/he_staining_done',
#                                    'baseline/number_of_positive_lymph_nodes_by_he_staining',
#                                    'baseline/clinical_staging_distant_metastasis', 'baseline/pathologic_staging_distant_metastasis',
#                                    'baseline/specify_distant_metastasis_documented_sites', 'baseline/residual_tumor',
#                                    'baseline/tumor_stage_pathological', 'baseline/paraneoplastic_syndrome_present',
#                                    'baseline/performance_status_assessment_ecog_performance_status_score',
#                                    'baseline/performance_status_assessment_karnofsky_performance_status_score',
#                                    'baseline/number_of_positive_lymph_nodes_by_ihc_staining', 'baseline/perineural_invasion',
#                                    'procurement/blood_collection_minimum_required_blood_collected',
#                                    'procurement/blood_collection_number_of_blood_tubes_collected',
#                                    'procurement/tumor_tissue_collection_tumor_type',
#                                    'procurement/tumor_tissue_collection_number_of_tumor_segments_collected',
#                                    'procurement/tumor_tissue_collection_clamps_used',
#                                    'procurement/tumor_tissue_collection_frozen_with_oct',
#                                    'procurement/normal_adjacent_tissue_collection_number_of_normal_segments_collected',
#                                    'Recurrence-free survival', 'Overall survial', 'Recurrence status (1, yes; 0, no)',
#                                    'Survial status (1, dead; 0, alive)']]
#             self._data['cancer_diagnosis'] = cancer_diagnosis_df

#             # Create followup df
#             followup_df = all_clinical[['follow-up/follow_up_period','follow-up/is_this_patient_lost_to_follow-up',
#                            'follow-up/vital_status_at_date_of_last_contact',
#                            'follow-up/days_from_date_of_initial_pathologic_diagnosis_to_date_of_last_contact',
#                            'follow-up/adjuvant_post-operative_radiation_therapy',
#                            'follow-up/adjuvant_post-operative_pharmaceutical_therapy',
#                            'follow-up/adjuvant_post-operative_immunological_therapy',
#                            'follow-up/tumor_status_at_date_of_last_contact_or_death',
#                            'follow-up/measure_of_success_of_outcome_at_the_completion_of_initial_first_course_treatment',
#                            'follow-up/measure_of_success_of_outcome_at_last_available_follow-up',
#                            'follow-up/eastern_cooperative_oncology_group_at_last_available_follow-up',
#                            'follow-up/karnofsky_score_preoperative_at_last_available_follow-up',
#                            'follow-up/performance_status_scale_timing_at_last_available_follow-up',
#                            'follow-up/measure_of_success_of_outcome_at_first_NTE',
#                            'follow-up/eastern_cooperative_oncology_group_at_first_NTE',
#                            'follow-up/karnofsky_score_preoperative_at_first_NTE',
#                            'follow-up/performance_status_scale_timing_at_first_NTE',
#                            'follow-up/new_tumor_after_initial_treatment',
#                            'follow-up/days_from_date_of_initial_pathologic_diagnosis_to_date_of_new_tumor_after_initial_treatment',
#                            'follow-up/type_of_new_tumor', 'follow-up/site_of_new_tumor', 'follow-up/other_site_of_new_tumor',
#                            'follow-up/diagnostic_evidence_of_recurrence_or_relapse', 'follow-up/additional_surgery_for_new_tumor',
#                            'follow-up/residual_tumor_after_surgery_for_new_tumor',
#                            'follow-up/additional_treatment_for_new_tumor_radiation',
#                            'follow-up/additional_treatment_for_new_tumor_pharmaceutical',
#                            'follow-up/additional_treatment_for_new_tumor_immunological',
#                            'follow-up/days_from_date_of_initial_pathologic_diagnosis_to_date_of_additional_surgery_for_new_tumor',
#                            'follow-up/cause_of_death', 'follow-up/days_from_date_of_initial_pathologic_diagnosis_to_date_of_death']]
#             self._data['followup'] =followup_df

#             categories = {'demographic': ['consent/', 'medications/', 'medical_history/'],
#                           'cancer_diagnosis': ['baseline/', 'cptac_path/', 'procurement/'],
#                           'followup': ['follow-up/']}

#             # remove general categories from column labels
#             for df_name in categories.keys():
#                 df = self._data[df_name]
#                 for c in categories[df_name]:
#                     df.columns = df.columns.str.replace(c, "")
#                     self._data[df_name] = df

#             if len(medical_conditions_df.index) != 0:
#                 df = self._data['medical_conditions']
#                 df.columns = df.columns.str.replace("general_medical_history/", "")
#                 df = df.assign(medical_condition = df.medical_condition.str.split("|"))
#                 df = df.assign(history_of_treatment = df.history_of_treatment.str.split("|"))
#                 df = df.assign(history_source = df.history_source.str.split("|"))
#                 exploded_df = df.apply(pd.Series.explode) # explode
#                 self._data['medical_conditions'] = exploded_df
                
#             if len(previous_cancer_df.index) != 0:
#                 pc = self._data['previous_cancer']
#                 pc.columns = pc.columns.str.replace('cancer_history/', "")
#                 pc = pc.assign(cancer_type = pc.cancer_type.str.split("|"))
#                 pc = pc.assign(history_source = pc.history_source.str.split("|"))
#                 pc = pc.assign(history_of_any_treatment = pc.history_of_any_treatment.str.split("|"))
#                 pc = pc.assign(medical_record_documentation_of_this_history_of_cancer_and_treatment = 
#                                pc.medical_record_documentation_of_this_history_of_cancer_and_treatment.str.split("|"))
#                 exploded_pc = pc.apply(pd.Series.explode)
#                 self._data['previous_cancer'] = exploded_pc

#             # make lists for vals in medication cols
#             dem = self._data['demographic']
#             dem = dem.assign(medication_name_vitamins_supplements = dem.medication_name_vitamins_supplements.str.split("|"))
#             dem = dem.assign(history_source = dem.history_source.str.split("|"))
#             dem = dem.rename(columns={'history_source':'med_history_source'}) # ?? ok to rename?
#             self._data['demographic'] = dem

