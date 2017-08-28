#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by j on 2017. 8. 14..
import argparse
import datetime
import json
import subprocess
import re
from commons.slack_webhook import SlackWebHooks


class CommonUtils:
    @staticmethod
    def init_argument():
        """
        Usage : ./foobar.py --profile=foo --region=ap-northeast-2 --slack=https://..../xxx/yyy/zzz
        :return: 
        """
        parser = argparse.ArgumentParser(description='Foobar Instances Scheduler arguments')
        parser.add_argument('--region', metavar='target_region_name', required=False, default='ap-northeast-2')
        parser.add_argument('--profile', metavar='aws_profiles', required=False, default='besty')
        parser.add_argument('--slack', metavar='slack_webhooks_key', required=False)
        parser.add_argument('--pem', metavar='pemfile path', required=False, default=None)
        args = parser.parse_args()

        SlackWebHooks.init_slack(args.slack)
        argument = {
            'aws_profile': args.profile,
            'aws_region': args.region,
            'slack_webhook_key': args.slack
        }
        if args.pem is not None:
            argument['pem'] = args.pem

        return argument

    @staticmethod
    def find_json_kv_query(data, name):
        val = None

        for d in data:
            if d['Key'] == name:
                val = d['Value']
                break

        return val


class DateUtils:
    @staticmethod
    def is_today_in_weekdays():
        current_week_day = datetime.datetime.now().strftime('%a').lower()
        # running days
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        if current_week_day in weekdays:
            return True
        return False

    @staticmethod
    def is_valid_scheduler_times(start_time, end_time):
        """
        :param start_time: 09:00 
        :param end_time: 18:00
        :return: 
        """
        # 현재 H:m 체크
        now_date = datetime.datetime.now()
        start_date = DateUtils.hm_to_date_time(start_time)
        stop_date = DateUtils.hm_to_date_time(end_time)
        # 현재 상태체크
        return start_date <= now_date <= stop_date

    @staticmethod
    def hm_to_date_time(hm):
        cur = datetime.datetime.now()
        hour = hm.split(':')[0]
        minute = hm.split(':')[1]
        date_time = cur.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        return date_time


class ScriptUtils:
    @staticmethod
    def run_shell(command, cwd=None):
        """
        Run shell
    
        :param command:
        :param cwd:
        :return:
        """
        popen = subprocess.Popen(command
                                 , stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                                 , cwd=cwd)
        for stdout_line in iter(popen.stdout.readline, b''):
            print(stdout_line.rstrip())

        popen.stdout.close()
        return_code = popen.wait()
        if return_code > 1:
            raise Exception(
                'Command failed on instance. An unexpected error has occurred [ErrorCode: {}]'.format(return_code))

    @staticmethod
    def parser_shell_result_to_json(str):
        """
        parsing bytes to json
    
        :param str:
        :return: json
        """
        # no \r in the output
        _, sep, json_parts = str.rpartition(b"\r")
        if not sep:
            json_parts = str
        jbytes = b"[" + re.sub(b"}( *){", b"}, {", json_parts) + b"]"
        return json.loads(jbytes.decode())[0]

    @staticmethod
    def parser_shell_result_to_string(str):
        """
        parsing bytes to string
    
        :param str:
        :return: string
        """
        # no \r in the output
        _, sep, json_parts = str.rpartition(b"\r")
        if not sep:
            json_parts = str
        jbytes = re.sub(b"", b"", json_parts) + b""
        return jbytes.decode()

    @staticmethod
    def run_awscli(command, is_json=True):
        """
        Run AWS CLI command in subprocess
    
        :param command:
        :param is_json:
        :return: Run AWS CLI result
        """
        result, error = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         shell=True).communicate()
        if error:
            print(error)

        if result:
            if is_json:
                return ScriptUtils.parser_shell_result_to_json(result)
            else:
                return ScriptUtils.parser_shell_result_to_string(result)
        else:
            return ''

    @staticmethod
    def run_aws_cli_with_query(aws_region, aws_profile, aws_cli, *args):
        """
        Run AWS CLI command formatting region, profile
    
        :param aws_region: 
        :param aws_profile: 
        :param aws_cli:
        :param args:
        :return: json
        """
        return ScriptUtils.run_awscli(aws_cli.format(*args, region=aws_region, profile=aws_profile))

    @staticmethod
    def run_aws_cli_with_query_to_string(aws_region, aws_profile, aws_cli, *args):
        """
        Run AWS CLI command formatting region, profile
    
        :param aws_profile: 
        :param aws_region: 
        :param aws_cli:
        :param args:
        :return: string
        """
        return ScriptUtils.run_awscli(aws_cli.format(*args, region=aws_region, profile=aws_profile), False)
