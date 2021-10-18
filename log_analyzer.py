#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


def send_message(_message: str, level: Optional[str] = 'i') -> None:
    """Send message to stdout and to log file at the same time

    Args:
        _message (str): message that need to send
        level (Optional[str], optional): 'i' - info level, 'w' - warning \
            level, 'error' - error level, 'exception' - exception level. \
            Defaults to 'i'.
    """
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
    default_config_keys = ['REPORT_DIR', 'LOG_DIR']
    default_log_file_name_pattern = r'nginx-access-ui\.log-[0-9]{8}(?:\.gz)?'
    default_log_file_date_pattern = r'nginx-access-ui\.log-([0-9]{8})(?:\.gz)?'
    default_row_pattern = re.compile(
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
        self.config_keys = self.default_config_keys
        self.log_file_name_pattern = self.default_log_file_name_pattern
        self.log_file_date_pattern = self.default_log_file_date_pattern
        self.row_pattern = self.default_row_pattern
        self.lines_count = 0
        self.errors = 0
        if not debug and not self.is_keys_in_config(config):
            _message = 'NOT PROPPER CONFIG'
            logger.exception(_message)
            raise Exception(_message)
        else:
            self.config = config

    def handle_log(self):
        if not self.is_ready_to_parse():
            return None
        log_file_path = self.get_log_file_path(self.config)
        parsed_log = self.parse_log(log_file_path)
        if not parsed_log:
            send_message("Log was not parsed", level='w')
            return None
        send_message(f'parsing {log_file_path}')
        self.export_report(self.get_report_dir(self.config), parsed_log)
        if self.errors:
            send_message(f'Parsing errors: {self.errors}', level='w')
        return True

    def is_ready_to_parse(self) -> bool:
        """Check if conditions meet requirements to start parsing log file

        Returns:
            bool: Is it possible to parse log or not
        """
        log_dir = self.get_log_dir(self.config)
        if not Path(log_dir).exists():
            send_message(f'Directory {log_dir} not found', level='w')
            return False
        if not os.listdir(log_dir):
            send_message(f'No files in {log_dir} directory', level='w')
            return False
        report_file_path = self.get_report_file_path(self.config)
        if Path(report_file_path).exists():
            send_message('Report already exists')
            return False  # all work already done - nothing to do
        return True  # ready to start parsing log file

    def get_log_dir(self, config: Dict) -> Path:
        log_dir = Path(config['LOG_DIR'])
        return log_dir

    def get_report_dir(self, config: Dict) -> Path:
        report_dir = Path(config['REPORT_DIR'])
        return report_dir

    def export_report(self, report_dir, parsed_log):
        Path(report_dir).mkdir(exist_ok=True, parents=True)
        self.create_report(self.get_report_file_path(self.config),
                           parsed_log)

    def get_report_file_path(self, config: Dict) -> str:
        """combine and return report file path

        Args:
            config (Dict): general configuration dict

        Returns:
            str: report file path
        """
        log_file_path = self.get_log_file_path(config)
        _dt = re.findall(self.log_file_date_pattern, log_file_path)[0]
        log_file_date = datetime.strptime(_dt, '%Y%m%d')
        if not log_file_date:
            return None
        report_dir = self.get_report_dir(self.config)
        formatted_date = log_file_date.strftime('%Y.%m.%d')
        report_file_name = f"report-{formatted_date}.html"
        return os.path.join(report_dir, report_file_name)

    def create_report(self, report_file_path, parsed_log):
        if Path(report_file_path).exists():
            return None
        with open('report_template.html', 'r', encoding='utf-8') as file:
            report_text = ''.join(file.readlines())
        with open(report_file_path, 'w', encoding='utf-8') as file:
            _template = Template(report_text)
            report_text = _template.safe_substitute(
                table_json=[*parsed_log.values()])
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

    def get_log_file_path(self, config: Dict) -> str:
        log_dir = self.get_log_dir(config)
        latest_file, max_date = '', 0
        log_files_list = self.get_files_list(log_dir)
        if not log_files_list:
            return None
        for file in log_files_list:
            if not re.fullmatch(self.log_file_name_pattern, file):
                continue
            file_date = int(file[20:28])
            if file_date > max_date:
                latest_file, max_date = file, file_date
        if not latest_file:
            return None
        return os.path.join(log_dir, latest_file)

    def get_files_list(self, dirrectory):
        files_list = os.listdir(dirrectory)
        if not files_list:
            send_message('No files in log directory')
            return None
        for file_name in files_list:
            if os.path.isfile(os.path.join(dirrectory, file_name)):
                yield file_name

    def parse_log(self, log_file_path):
        result_dict = {}
        lines_count, total_request_time = 0, .0
        log_file = gzip.open(log_file_path, 'rt') if (
            log_file_path.endswith('.gz')
        ) else open(log_file_path, 'r', encoding='utf-8')
        if not log_file:
            return None
        for row in log_file:
            lines_count += 1
            parsed = self.parse_log_row(row, self.row_pattern)
            if not parsed:
                self.errors += 1
                continue
            total_request_time += float(parsed['request_time'])
            request, request_time = parsed['request'], parsed['request_time']
            if request not in result_dict:
                temp_dict = {
                    'url': request,
                    'count': 1,
                    'durations': [request_time],
                    'time_avg': request_time,
                    'time_max': request_time,
                    'time_sum': request_time,
                }
            else:
                temp_dict = result_dict[request]
                temp_dict['count'] += 1
                temp_dict['durations'].append(request_time)
                temp_dict['time_sum'] += request_time
                temp_dict['time_avg'] = (
                    temp_dict['time_sum'] / temp_dict['count'])
                temp_dict['time_max'] = request_time if (
                    request_time > temp_dict['time_max']
                                 ) else temp_dict['time_max']
            result_dict[request] = temp_dict
        log_file.close()

        for key in result_dict:
            result_dict[key]['count_perc'] = (
                result_dict[key]['count'] * 100 / lines_count)
            result_dict[key]['time_perc'] = (
                result_dict[key]['time_sum'] * 100 / total_request_time)
            durations = result_dict[key]['durations']
            result_dict[key]['time_med'] = (
                durations[0] if len(durations) == 1 else median(durations))
            del result_dict[key]['durations']
        return result_dict

    def parse_log_row(self, parsing_string: str, row_pattern: str) -> Dict:
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
            log_parser.handle_log()
        except:  # noqa: E722
            logger.exception(f'uncaught exception: {traceback.format_exc()}')
    send_message('End process\n')


if __name__ == "__main__":
    main()
