#!/usr/bin/env python
# -*- coding: utf-8 -*-

# DONE add logs
# DONE make generator function for parsing
# DONE add workaround about empty log dirrectory
# TODO add custom configs
# TODO add unittests
# TODO add warning about a lot of parsing errors
# TODO add docstrings for functions
# TODO add README.md

# log_format ui_short
# '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
# '$status $body_bytes_sent "$http_referer" '
# '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" '
# '"$http_X_RB_USER" $request_time';

import argparse
import gzip
import logging
import os
import re
import traceback
from datetime import datetime
from string import Template

config = {
    "REPORT_SIZE": 1000,
    # "REPORT_DIR": "./reports",
    "REPORT_DIR": os.path.join('.', 'reports'),
    # "LOG_DIR": "./log"
    "LOG_DIR": os.path.join('.', 'log')
}


# setup logger
logging.basicConfig(
    filename=datetime.today().strftime('%Y%m%d') + '.log',
    format='[%(asctime)s] %(levelname).1s %(message)s',
    datefmt='%Y.%m.%d %H:%M:%S',
    encoding='utf-8',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class LogParser:
    """[summary]

    Raises:
        Exception: [description]

    Returns:
        [type]: [description]

    Yields:
        [type]: [description]
    """
    config_keys = ['REPORT_DIR', 'LOG_DIR']
    report_dir = ''
    log_dir = ''
    log_file_path = ''
    log_file_date = None
    report_file_path = ''
    lines_count = 0
    errors = 0
    parsed_log = dict()
    log_file_name_pattern = r'nginx-access-ui.log-[0-9]{8}(?:.gz)'
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

    def __init__(self, _config=None):
        if _config is None:
            print('Using default config')
            logger.info('Using default config')
            _config = config
        if self.is_keys_in_config(_config):
            self.report_dir = _config['REPORT_DIR']
            self.log_dir = _config['LOG_DIR']
        else:
            raise Exception('NOT PROPPER CONFIG')
        if not self.is_logs_exists():
            print('Log files not found, end program')
            logger.warning('Log files not found, end program')
            return None
        if self.is_report_exists():
            print('Nothing to process, end program')
            logger.warning('Nothing to process, end program')
            return None
        print(f'parsing {self.log_file_path}')
        logger.info(f'parsing {self.log_file_path}')
        self.parsed_log = self.get_parsed_log()
        self.export_report()

    def export_report(self):
        if not os.path.exists(self.report_dir):
            os.mkdir(self.report_dir)
        self.create_report()

    def get_report_file_path(self):
        if not self.log_file_path or not self.log_file_date:
            self.get_log_file_path_and_date()
        if not self.report_file_path:
            report_file_name = (
                'report-' +
                self.log_file_date.strftime('%Y.%m.%d') +
                '.html'
            )
            self.report_file_path = os.path.join(
                self.report_dir, report_file_name
            )
        return self.report_file_path

    def is_logs_exists(self):
        if os.path.exists(self.log_dir):
            if self.get_latest_log_file_path():
                return True
        return False

    def is_report_exists(self):
        self.report_file_path = self.get_report_file_path()
        if os.path.exists(self.report_file_path):
            return True
        return False

    def create_report(self):
        self.report_file_path = self.get_report_file_path()
        if not os.path.exists(self.report_file_path):
            with open('report.html', 'r', encoding='utf-8') as file:
                report_text = ''.join(file.readlines())
            with open(self.report_file_path, 'w', encoding='utf-8') as file:
                _template = Template(report_text)
                report_text = _template.safe_substitute(
                    table_json=[*self.parsed_log.values()]
                )
                file.writelines(report_text)
        print(f'{self.report_file_path} created')
        logger.info(f'{self.report_file_path} created')

    def is_keys_in_config(self, _config, keys=None):
        print(f'CONFIG: {_config}')
        logger.info(f'CONFIG: {_config}')
        if not keys:
            keys = self.config_keys
        for key in keys:
            if key not in _config:
                return False
        return True

    def get_log_file(self):
        if not self.log_file_path or not self.log_file_date:
            self.get_log_file_path_and_date()
        if self.log_file_path.endswith('.gz'):
            _file = gzip.open(self.log_file_path, 'rt')
        else:
            _file = open(self.log_file_path, 'r', encoding='utf-8')
        return (row for row in _file)

    def get_log_file_path_and_date(self):
        if not self.log_file_path:
            self.log_file_path = self.get_latest_log_file_path()
        if not self.log_file_date:
            self.log_file_date = self.get_latest_log_file_date()
        return self.log_file_path, self.log_file_date

    def get_latest_log_file_path(self):
        if not os.listdir(self.log_dir):
            return None
        _files_list = os.listdir(self.log_dir)
        if not re.findall(self.log_file_name_pattern, '\n'.join(_files_list)):
            return None
        files_dict, max_date = dict(), 0
        files_list = self.get_files_list()
        for file in files_list:
            file_date = int(file[20:28])
            max_date = file_date if file_date > max_date else max_date
            files_dict[file_date] = file
        return os.path.join(self.log_dir, files_dict[max_date])

    def get_latest_log_file_date(self):
        pattern = r'nginx-access-ui.log-([0-9]{8})(?:.gz)?'  # get ['YYYYmmdd']
        _date = re.findall(pattern, self.log_file_path)[0]
        format_date = '%Y%m%d'
        return datetime.strptime(_date, format_date)

    def get_files_list(self):
        content = os.listdir(self.log_dir)
        for file_name in content:
            if (
                os.path.isfile(os.path.join(self.log_dir, file_name))
                and re.fullmatch(self.log_file_name_pattern, file_name)
            ):
                # print(file_name)
                yield file_name

    def get_lines_count(self):
        if not self.lines_count:
            self.count_lines_and_total_request_time()
        return self.lines_count

    def get_total_request_time(self):
        if not self.total_request_time:
            self.count_lines_and_total_request_time()
        return self.total_request_time

    def count_lines_and_total_request_time(self):
        if not self.lines_count or not self.total_request_time:
            log_file = self.get_log_file()
            self.lines_count = 0
            self.total_request_time = 0
            for row in log_file:
                self.lines_count += 1
                parsed = self.parse_log_row(row)
                if parsed:
                    self.total_request_time += float(
                        parsed['request_time']
                    )

    def get_parsed_log(self):
        log_file, result_dict = self.get_log_file(), dict()
        self.lines_count = self.get_lines_count()
        self.total_request_time = self.get_total_request_time()
        for row in log_file:
            parsed = self.parse_log_row(row)
            if not parsed:
                self.errors += 1
                continue
            request, request_time = parsed['request'], parsed['request_time']
            if request not in result_dict:
                tr_dict = {
                    'url': request,
                    'count': 1,
                    'durations': [request_time],
                    'count_perc': 100 / self.lines_count,
                    'time_avg': request_time,
                    'time_max': request_time,
                    'time_sum': request_time,
                    'time_perc': request_time * 100 / self.total_request_time
                }
            else:
                tr_dict = result_dict[request]
                tr_dict['count'] += 1
                tr_dict['durations'].append(request_time)
                tr_dict['count_perc'] = (
                    tr_dict['count'] * 100 / self.lines_count
                )
                tr_dict['time_sum'] += request_time
                tr_dict['time_perc'] = (
                    tr_dict['time_sum'] * 100 / self.total_request_time
                )
                tr_dict['time_avg'] = tr_dict['time_sum'] / tr_dict['count']
                tr_dict['time_max'] = request_time if (
                                          request_time > tr_dict['time_max']
                                      ) else tr_dict['time_max']
            result_dict[request] = tr_dict

        for key in result_dict:
            durations = result_dict[key]['durations']
            result_dict[key]['time_med'] = durations[0] if (
                                               len(durations) == 1
                                           ) else self.median(durations)
            del result_dict[key]['durations']
        return result_dict

    def median(self, lst):
        s, n = sorted(lst), len(lst)
        index = (n - 1) // 2
        if (n % 2):
            return s[index]
        else:
            return (s[index] + s[index + 1])/2.0

    def parse_log_row(self, parsing_string):
        try:
            transition_list = re.findall(self.row_pattern, parsing_string)[0]
        except:  # noqa: E722
            return False
        result_dict = {
            'remote_addr': transition_list[0],
            'remote_user': transition_list[1],
            'http_x_real_ip': transition_list[2],
            'time_local': transition_list[3],
            'request': transition_list[4],
            'status': transition_list[5],
            'body_bytes_sent': int(transition_list[6]),
            'http_referer': transition_list[7],
            'http_user_agent': transition_list[8],
            'http_x_forwarded_for': transition_list[9],
            'http_X_REQUEST_ID': transition_list[10],
            'http_X_RB_USER': transition_list[11],
            'request_time': float(transition_list[12])
        }
        return result_dict


def get_custom_config(path):
    # if config path exists
    # get args from path 
    pass


def main():
    parser = argparse.ArgumentParser(description='Configuration file')
    parser.add_argument(
        '-c',
        '--config',
        type=str,
        # default='config',
        help='Path to custom configuration file'
    )
    args = parser.parse_args()
    if args:
        print(f'ARGS: {args}')
        print(f'ARGS2: {args.config}')
        print(get_custom_config(args))
        return None
    print('Start process')
    logger.info('Start process')
    try:
        LogParser(_config=config)
    except:  # noqa: E722
        # logger.error(f'uncaught exception: {traceback.format_exc()}')
        logger.exception(f'uncaught exception: {traceback.format_exc()}')
    print('End process')
    logger.info('End process')


if __name__ == "__main__":
    main()
