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

class TestLoad:
    '''
    A class for testing the loading of datasets

    Methods
    -------
    test_datasets_download:
        test downloading the datasets
    test_invalid_dataset:
        verify that the correct error is raised for attempting to download a non-existent dataset
    test_dataset_object_creation:
        verifies that all the Cancer objects have been created for further tests
    '''

    def test_datasets_download(self, download_datasets):
        assert download_datasets

    def test_invalid_dataset(self):
        with pytest.raises(InvalidParameterError) as exception_raised:
            cptac.download("abc")
        assert exception_raised.type == InvalidParameterError
    
    def test_dataset_object_creation(self, get_cancer_test_units):
        assert get_cancer_test_units