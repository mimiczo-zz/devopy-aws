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
    Simple AWS RDS instances Start/Stop Scheduler Management
    
    Usage : ./rds.py --profile=foo --region=ap-northeast-2 --slack=https://..../xxx/yyy/zzz

"""
def main():
    SEND_MESSAGES.append('>>>>> RDS Scheduler is starting. Start Time : {}'.format(datetime.datetime.now()))

    is_running_day = DateUtils.is_today_in_weekdays()
    boto_client = BotoUtils(AwsService.RDS, GLOBAL_PARAMETER['aws_profile'], GLOBAL_PARAMETER['aws_region']).get_client()

    if is_running_day:
        result_db_instances = boto_client.describe_db_instances()

        if len(result_db_instances['DBInstances']) == 0:
            SEND_MESSAGES.append('  >>>>> Not Found Target RDS instances')
            return

        for r in result_db_instances['DBInstances']:
            rds_resource_name = r['DBInstanceArn']
            rds_instance_identifier = r['DBInstanceIdentifier']
            result_tags = boto_client.list_tags_for_resource(ResourceName=rds_resource_name)

            scheduler_times = ''
            for t in result_tags['TagList']:
                if t['Key'] == 'SchedulerTime':
                    scheduler_times = t['Value'].split('-')
                if t['Key'] == 'workload-type' and t['Value'] == 'production':
                    scheduler_times = ''

            if scheduler_times:
                start_time = scheduler_times[0]
                end_time = scheduler_times[1]
                is_valid_scheduler_times = DateUtils.is_valid_scheduler_times(start_time, end_time)

                if r['DBInstanceStatus'] == 'available' and is_valid_scheduler_times is False:
                    SEND_MESSAGES.append('  >>>>> RDS running time [{}][{}]: {} ~ {}'.format(rds_resource_name, is_valid_scheduler_times, start_time, end_time))
                    SEND_MESSAGES.append('  >>>>> Stopping Target RDS(s) [{}]-[{}]'.format(rds_resource_name, rds_instance_identifier))
                    result_done = boto_client.stop_db_instance(DBInstanceIdentifier=rds_instance_identifier)
                    if result_done['DBInstance']['DBInstanceIdentifier'] == rds_instance_identifier:
                        SLACK_OPTIONS_PARAMETER['is_send'] = True
                elif r['DBInstanceStatus'] == 'stopped' and is_valid_scheduler_times is True:
                    SEND_MESSAGES.append('  >>>>> RDS running time [{}][{}]: {} ~ {}'.format(rds_resource_name, is_valid_scheduler_times, start_time, end_time))
                    SEND_MESSAGES.append('  >>>>> Starting Target RDS(s) [{}]-[{}]'.format(rds_resource_name, rds_instance_identifier))
                    result_done = boto_client.start_db_instance(DBInstanceIdentifier=rds_instance_identifier)
                    if result_done['DBInstance']['DBInstanceIdentifier'] == rds_instance_identifier:
                        SLACK_OPTIONS_PARAMETER['color'] = '#36a64f'
                        SLACK_OPTIONS_PARAMETER['is_send'] = True

    if SLACK_OPTIONS_PARAMETER['is_send'] is False:
        SEND_MESSAGES.append('  >>>>> Not Found Target RDS instances that SchedulerTime conditions')


if __name__ == '__main__':
    try:
        main()
    except:
        print(traceback.format_exc())
    finally:
        print('\n'.join(SEND_MESSAGES))
        if SLACK_OPTIONS_PARAMETER['is_send']:
            SlackWebHooks.post_slack('\n'.join(SEND_MESSAGES), 'Scheduler', SLACK_OPTIONS_PARAMETER['color'])