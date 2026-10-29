import unittest
from unittest.mock import patch
from dialog_inspection import inspect_url


class InspectionAdapterTests(unittest.TestCase):
    def test_file_metadata_retains_kind_size_and_validated_redirect_url(self):
        metadata=dict(kind='file',url='https://example.invalid/final',filename='fixture.zip',filesize=42,supports_ranges=True)
        with patch('browser_files.prepare_transfer',return_value=metadata) as prepare:
            result=inspect_url('https://example.invalid/source')
        self.assertEqual(result,metadata);prepare.assert_called_once_with('https://example.invalid/source')

    def test_http_failures_are_not_silently_reported_as_success(self):
        with patch('browser_files.prepare_transfer',side_effect=ValueError('Synthetic refusal')):
            with self.assertRaisesRegex(ValueError,'Synthetic refusal'):inspect_url('https://example.invalid/source')


if __name__=='__main__':unittest.main()
