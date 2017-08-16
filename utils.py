#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by j on 2017. 8. 16..
import json
import subprocess
import re


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
        result, error = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
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