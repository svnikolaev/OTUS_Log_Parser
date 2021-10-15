#!/usr/bin/env python
# -*- coding: utf-8 -*-

# DONE add README.md
# DONE add logs
# DONE make generator function for parsing
# DONE add workaround about empty log directory
# DONE add custom configs
# DONE add unittests
# DONE add warning about a lot of parsing errors

# log_format ui_short
# '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
# '$status $body_bytes_sent "$http_referer" '
# '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" '
# '"$http_X_RB_USER" $request_time';

import argparse
import configparser
import gzip
import logging
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from statistics import median
from string import Template
from typing import Dict, Optional

# setup logger
logging.basicConfig(
    filename=datetime.today().strftime('%Y%m%d') + '.log',
    format='[%(asctime)s] %(levelname).1s %(message)s',
    datefmt='%Y.%m.%d %H:%M:%S',
    encoding='utf-8',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def send_message(_message, level='i'):
    print(_message)
    if level == 'i':
        logger.info(_message)
    if level == 'w':
        logger.warning(_message)
    if level == 'error':
        logger.error(_message)
    if level == 'exception':
        logger.exception(_message)


class LogParser:
    config_keys = ['REPORT_DIR', 'LOG_DIR']
    log_file_name_pattern = r'nginx-access-ui\.log-[0-9]{8}(?:\.gz)?'
    log_file_date_pattern = r'nginx-access-ui\.log-([0-9]{8})(?:\.gz)?'
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

    def __init__(self, config: Dict, debug: Optional[bool] = False) -> None:
        self.report_dir = ''
        self.log_dir = ''
        self.log_file_path = ''
        self.log_file_date = None
        self.report_file_path = ''
        self.lines_count = 0
        self.errors = 0
        if not debug and not self.is_keys_in_config(config):
            _message = 'NOT PROPPER CONFIG'
            logger.exception(_message)
            raise Exception(_message)
        self.config = config
        self.log_dir = self.get_log_dir(config)

    def is_ready_to_parse(self, config):
        log_dir = self.get_log_dir(config)
        if not os.path.exists(log_dir):
            send_message(f'Directory {log_dir} not found', level='w')
            return False
        if not os.listdir(log_dir):
            send_message(f'No files in {log_dir} directory', level='w')
            return False
        if self.is_report_exists(
            self.get_report_file_path(
                self.get_report_dir(config)
            )
        ):
            send_message('Report already exists')
            return False
        return True

    def get_log_dir(self, config):
        if not self.log_dir:
            log_dir = Path(config['LOG_DIR'])
            # log_dir = os.path.join(
            #     *config['LOG_DIR'].replace('\\', '/').split('/'))
            # print(f'log_dir: {log_dir}')
            self.log_dir = log_dir
        return self.log_dir

    def get_report_dir(self, config):
        if not self.report_dir:
            report_dir = Path(config['REPORT_DIR'])
            # report_dir = os.path.join(
            #     *config['REPORT_DIR'].replace('\\', '/').split('/'))
            print(f'report_dir: {report_dir}')
            self.report_dir = report_dir
        return self.report_dir

    def is_report_exists(self, report_file_path) -> bool:
        if os.path.exists(report_file_path):
            return True
        return False

    def parse_log_file(self):
        config = self.config
        if not self.is_ready_to_parse(config):
            return None
        log_file_path = self.get_log_file_path()
        parsed_log = self.get_parsed_log(log_file_path)
        if not parsed_log:
            return None
        send_message(f'parsing {self.log_file_path}')
        self.export_report(
            self.get_report_dir(config),
            parsed_log
        )
        if self.errors:
            send_message(f'Parsing errors: {self.errors}', level='w')

    def export_report(self, report_dir, parsed_log):
        if not os.path.exists(report_dir):
            os.mkdir(report_dir)
        self.create_report(
            self.get_report_file_path(report_dir),
            parsed_log
        )

    def get_report_file_path(self, report_dir, date=None):
        if date is None:
            date = self.get_log_file_date()
        if not date:
            return None
        if not self.report_file_path:
            formatted_date = date.strftime('%Y.%m.%d')
            report_file_name = f"report-{formatted_date}.html"
            self.report_file_path = os.path.join(
                report_dir, report_file_name)
        return self.report_file_path

    def create_report(self, report_file_path, parsed_log):
        if not os.path.exists(self.report_file_path):
            with open('report_template.html', 'r', encoding='utf-8') as file:
                report_text = ''.join(file.readlines())
            with open(report_file_path, 'w', encoding='utf-8') as file:
                _template = Template(report_text)
                report_text = _template.safe_substitute(
                    table_json=[*parsed_log.values()]
                )
                file.writelines(report_text)
        send_message(f'{report_file_path} created')
        return True

    def is_keys_in_config(self, config, keys=None, debug=False):
        if keys is None:
            keys = self.config_keys
        if not debug:
            send_message(f'CONFIG: {config}')
        for key in keys:
            if key not in config:
                if not debug:
                    send_message(f'Config key: {key} not in config', level='w')
                return False
        return True

    def get_log_file(self, log_file_path=None):
        if log_file_path is None:
            log_file_path = self.get_log_file_path()
        if not log_file_path:
            return None
        if self.log_file_path.endswith('.gz'):
            _file = gzip.open(self.log_file_path, 'rt')
        else:
            _file = open(self.log_file_path, 'r', encoding='utf-8')
        return (row for row in _file)

    def get_log_file_path(self):
        if not self.log_file_path:
            log_file_path = self.get_latest_log_file_path(
                self.get_log_dir(self.config)
            )
            if not log_file_path:
                return None
            self.log_file_path = log_file_path
        return self.log_file_path

    def get_log_file_date(self):
        if not self.log_file_date:
            self.log_file_date = self.get_latest_log_file_date()
        return self.log_file_date

    def get_log_files_list(self, log_dir):
        files_list = os.listdir(log_dir)
        if not files_list:
            send_message('No files in log directory')
            return None
        for file_name in files_list:
            if os.path.isfile(os.path.join(log_dir, file_name)):
                yield file_name

    def get_log_files_list_by_pattern(self, files_list=None, pattern=None):
        if not pattern:
            pattern = self.log_file_name_pattern
        if files_list is None:
            files_list = self.get_log_files_list(
                self.get_log_dir(self.config)
            )
        if not files_list:
            return None
        for file_name in files_list:
            if re.fullmatch(pattern, file_name):
                yield file_name

    def get_latest_log_file_path(self, log_dir):
        files_dict, max_date = {}, 0
        files_list = self.get_log_files_list_by_pattern()
        if not files_list:
            return None
        for file in files_list:
            file_date = int(file[20:28])
            max_date = file_date if file_date > max_date else max_date
            files_dict[file_date] = file
        if not files_dict:
            return None
        return os.path.join(log_dir, files_dict[max_date])

    def get_latest_log_file_date(self, log_file_path=None, pattern=None):
        if log_file_path is None:
            log_file_path = self.get_log_file_path()
        if not log_file_path:
            return None
        if pattern is None:
            pattern = self.log_file_date_pattern  # get ['YYYYmmdd']
        _date = re.findall(pattern, log_file_path)[0]
        format_date = '%Y%m%d'
        return datetime.strptime(_date, format_date)

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
        return True

    def get_parsed_log(self, log_file_path):
        log_file = self.get_log_file(log_file_path)
        result_dict = {}
        if not log_file:
            return None
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
                                           ) else median(durations)
            del result_dict[key]['durations']
        return result_dict

    def parse_log_row(self, parsing_string, row_pattern=None):
        if row_pattern is None:
            row_pattern = self.row_pattern
        try:
            transition_list = re.findall(row_pattern, parsing_string)[0]
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


def get_config() -> Dict:
    config = {
        "REPORT_SIZE": 1000,
        "REPORT_DIR": "./reports",
        "LOG_DIR": "./log"
    }
    parser = argparse.ArgumentParser(description='Configuration file')
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.ini',
        help='Path to configuration file'
    )
    config_path = parser.parse_args().config
    if not os.path.exists(config_path):
        send_message(f'Configuration file: {config_path} - is not exists',
                     level='w')
        return None
    config_parser = configparser.ConfigParser()  # create parser object
    config_parser.read(config_path)
    configuration = config_parser['LOG_PARSER']
    if configuration.get('REPORT_SIZE'):
        config['REPORT_SIZE'] = configuration.get('REPORT_SIZE')
    if configuration.get('REPORT_DIR'):
        config['REPORT_DIR'] = configuration.get('REPORT_DIR')
    if configuration.get('LOG_DIR'):
        config['LOG_DIR'] = configuration.get('LOG_DIR')
    return config


def main():
    send_message('Start process')
    config = get_config()
    if config:
        try:
            log_parser = LogParser(config)
            log_parser.parse_log_file()
        except:  # noqa: E722
            logger.exception(f'uncaught exception: {traceback.format_exc()}')
    send_message('End process\n')


if __name__ == "__main__":
    main()
