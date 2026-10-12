import unittest
from unittest.mock import patch
from browser_files import validate_file_url, prepare_transfer


class FileSafetyTests(unittest.TestCase):
    def test_private_address_rejected(self):
        with patch.dict('os.environ',{'SDM_ALLOW_LOCAL_TEST_URLS':'0'}), patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',80))]):
            with self.assertRaises(ValueError):validate_file_url('http://example.com/file')

    def test_mixed_public_private_dns_rejected(self):
        with patch.dict('os.environ',{'SDM_ALLOW_LOCAL_TEST_URLS':'0'}), patch('socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',80)),(2,1,6,'',('192.168.1.1',80))]):
            with self.assertRaises(ValueError):validate_file_url('https://example.com/file')

    def test_embedded_credentials_and_blob_rejected(self):
        for url in ['blob:https://example.com/id','file:///C:/test','https://user:pass@example.com/file']:
            with self.subTest(url=url),self.assertRaises(ValueError):validate_file_url(url)

    def test_public_address_accepted(self):
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]):
            self.assertEqual(validate_file_url('https://example.com/file'),'https://example.com/file')
