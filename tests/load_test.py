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

import pytest
import cptac
from cptac.exceptions import InvalidParameterError 

'''class for testing the loading of datasets'''
class TestLoad:

    @pytest.fixture(scope="session")
    def test_public_datasets(self, get_public_datasets):
        cancer_dict = {}
        for cancer_data_set in get_public_datasets:
            # TODO: add way to see dataset-specific failures
            assert cptac.download(cancer_data_set.lower(), redownload=True)
            cancer = getattr(cptac, cancer_data_set)
            try:
                cancer_dict[cancer] = cancer()
            except:
                pytest.fail(f"unable to create {cancer} object")
    
    """ def test_protected_datasets(self, get_restricted_datasets):
        for cancer_data_set in get_restricted_datasets:
            # TODO: figure out how to handle passwords
            # could add a directory outside of the package that contains a dict of the passwords.
            #   Then figure out how to import that dict
            #   The problem here is that other users with password access trying to run tests would have to know how to set up the files
            # could figure out how to prompt a system file selection that contains json for the passwords and import that data
            # could do nothing and let people type them in manually
            assert cptac.download(cancer_data_set.lower(), redownload=True)

            # TODO: add an assertion error test to handle situations when a file is missing a password but it shouldnt' be
            '''
            Error output:
                token = token_tag.get("value")
                AttributeError: 'NoneType' object has no attribute 'get'
            ''' """

    def test_invalid_dataset(self):
        with pytest.raises(InvalidParameterError) as exception_raised:
            cptac.download("abc")
        assert exception_raised.type == InvalidParameterError
    
