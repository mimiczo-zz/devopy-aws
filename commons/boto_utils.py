#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by j on 2017. 8. 23..
import boto3
from enum import Enum


class AwsService(Enum):
    EC2 = 'ec2'
    RDS = 'rds'
    S3 = 's3'
    DynamoDB = 'dynamodb'


class BotoUtils:
    def __init__(self, service_name=AwsService.EC2, profile=None, region='ap-northeast-2'):
        if type(service_name) is not AwsService:
            raise AttributeError('Parameters must AwsService.Enum')

        # get resources
        boto3.setup_default_session(profile_name=profile)
        client = boto3.client(service_name.value, region_name=region)
        self.__client = client

    def get_client(self):
        return self.__client