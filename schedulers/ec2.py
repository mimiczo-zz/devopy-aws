#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by j on 2017. 8. 28..
import datetime
import traceback
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from commons.utils import DateUtils, CommonUtils
from commons.slack_webhook import SlackWebHooks
from commons.boto_utils import BotoUtils, AwsService

SEND_MESSAGES = []
GLOBAL_PARAMETER = CommonUtils.init_argument()
SLACK_OPTIONS_PARAMETER = {
    'is_send': False,
    'color': '#FF0000'
}


"""
    Simple AWS EC2 instances Start/Stop Scheduler Management
    
    Usage : ./ec2.py --profile=foo --region=ap-northeast-2 --slack=https://..../xxx/yyy/zzz
"""
def main():
    SEND_MESSAGES.append('>>>>> Instances Scheduler is starting. Start Time : {}'.format(datetime.datetime.now()))

    is_running_day = DateUtils.is_today_in_weekdays()
    boto_client = BotoUtils(AwsService.EC2, GLOBAL_PARAMETER['aws_profile'], GLOBAL_PARAMETER['aws_region']).get_client()

    if is_running_day:
        result_instances = boto_client.describe_instances(Filters=[{'Name': 'tag:SchedulerTime', 'Values': ['*']}])

        if len(result_instances['Reservations']) == 0:
            SEND_MESSAGES.append('  >>>>> Not Found Target EC2 instances')
            return

        for r in result_instances['Reservations']:
            target_instance = r['Instances'][0]
            instance_id = target_instance['InstanceId']
            instance_name = CommonUtils.find_json_kv_query(target_instance['Tags'], 'Name')
            scheduler_times = CommonUtils.find_json_kv_query(target_instance['Tags'], 'SchedulerTime').split('-')

            start_time = scheduler_times[0]
            end_time = scheduler_times[1]
            is_valid_scheduler_times = DateUtils.is_valid_scheduler_times(start_time, end_time)

            if target_instance['State']['Name'] == 'running' and is_valid_scheduler_times is False:
                SEND_MESSAGES.append('  >>>>> Instances running time [{}][{}]: {} ~ {}'.format(instance_name, is_valid_scheduler_times, start_time, end_time))
                SEND_MESSAGES.append('  >>>>> Stopping Target instance(s) [{}]-[{}]'.format(instance_name, instance_id))
                result_done = boto_client.stop_instances(InstanceIds=[instance_id])
                if result_done['StoppingInstances'][0]['InstanceId'] == instance_id:
                    SLACK_OPTIONS_PARAMETER['is_send'] = True
            elif target_instance['State']['Name'] == 'stopped' and is_valid_scheduler_times is True:
                SEND_MESSAGES.append('  >>>>> Instances running time [{}][{}]: {} ~ {}'.format(instance_name, is_valid_scheduler_times, start_time, end_time))
                SEND_MESSAGES.append('  >>>>> Starting Target instance(s) [{}]-[{}]'.format(instance_name, instance_id))
                result_done = boto_client.start_instances(InstanceIds=[instance_id])
                if result_done['StartingInstances'][0]['InstanceId'] == instance_id:
                    SLACK_OPTIONS_PARAMETER['color'] = '#36a64f'
                    SLACK_OPTIONS_PARAMETER['is_send'] = True

    if SLACK_OPTIONS_PARAMETER['is_send'] is False:
        SEND_MESSAGES.append('  >>>>> Not Found Target EC2 instances that SchedulerTime conditions')


if __name__ == "__main__":

    try:
        main()
    except:
        print(traceback.format_exc())
    finally:
        print('\n'.join(SEND_MESSAGES))
        if SLACK_OPTIONS_PARAMETER['is_send']:
            SlackWebHooks.post_slack('\n'.join(SEND_MESSAGES), 'Scheduler', SLACK_OPTIONS_PARAMETER['color'])