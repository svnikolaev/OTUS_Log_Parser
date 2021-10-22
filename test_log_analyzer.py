import re
import unittest

from log_analyzer import LogParser


class TestLogParser(unittest.TestCase):
    def setUp(self):
        config = {
            "REPORT_SIZE": 1000,
            "REPORT_DIR": "./reports",
            "LOG_DIR": "./log"
        }
        self.log_parser = LogParser(config, debug=True)

    def test_check_config_params(self):
        for value, result in [
            ({
                "REPORT_SIZE": 1000,
                "REPORT_DIR": "./reports",
                "LOG_DIR": "./log"
            }, True),
            ({
                "REPORT_SIZE": 1000,
                "REPORT_DIR": "./reports",
            }, False),
            ({
                "REPORT_SIZE": 1000,
                "LOG_DIR": "./log"
            }, False),
            ({
                "REPORT_DIR": "./reports",
                "LOG_DIR": "./log"
            }, False),
            ({
                "REPORT_SIZE": 1000,
                "REPORT_DIR": "./reports",
                "LOG_DIR": "./log",
                "TEST_WASTE": 777
            }, True)
        ]:
            with self.subTest(value):
                self.assertEqual(
                    self.log_parser.check_config_params(
                        value,
                        params=['REPORT_DIR', 'LOG_DIR', 'REPORT_SIZE'],
                        debug=True
                    ),
                    result
                )

    def test_parse_log_row(self):
        parsing_string = '1.99.174.176 3b81f63526fa8  - [29/Jun/2017:03:50:22 +0300] "GET /api/1/photogenic_banners/list/?server_name=WIN7RB4 HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498697422-32900793-4708-9752770" "-" 0.133'  # noqa E501
        row_pattern = re.compile(
            r'''([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s*  # $remote_addr
                ([^\s]+)\s*  # $remote_user
                ([^\s]+)\s*  # $http_x_real_ip
                \[([^\]]+)\]\s*  # $time_local
                "[^\s]+\s([^\s]+)\s[^\s]+"\s*  # $request
                ([\d]+)\s*  # $status
                ([\d]+)\s*  # $body_bytes_sent
                "([^"]+)"\s*  # $http_referer
                "([^"]+)"\s*  # $http_user_agent
                "([^"]+)"\s*  # $http_x_forwarded_for
                "([^"]+)"\s*  # $http_X_REQUEST_ID
                "([^"]+)"\s*  # $http_X_RB_USER
                ([0-9\.]+)  # $request_time
            ''', re.VERBOSE)
        result_dict = {
            'remote_addr': '1.99.174.176',
            'remote_user': '3b81f63526fa8',
            'http_x_real_ip': '-',
            'time_local': '29/Jun/2017:03:50:22 +0300',
            'request': '/api/1/photogenic_banners/list/?server_name=WIN7RB4',
            'status': '200',
            'body_bytes_sent': 12,
            'http_referer': '-',
            'http_user_agent': 'Python-urllib/2.7',
            'http_x_forwarded_for': '-',
            'http_X_REQUEST_ID': '1498697422-32900793-4708-9752770',
            'http_X_RB_USER': '-',
            'request_time': 0.133
        }
        self.assertEqual(
            self.log_parser.parse_log_row(parsing_string, row_pattern),
            result_dict
        )


if __name__ == '__main__':
    unittest.main()
