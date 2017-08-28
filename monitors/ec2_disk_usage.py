#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by j on 2017. 7. 19..
import datetime
import re
import traceback
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from commons.boto_utils import BotoUtils, AwsService
from commons.slack_webhook import SlackWebHooks
from commons.utils import ScriptUtils, CommonUtils


SEND_MESSAGES = []
GLOBAL_PARAMETER = CommonUtils.init_argument()
SLACK_OPTIONS_PARAMETER = {
    'is_send': False,
    'color': '#FF0000'
}
# TODO : 80% 이상의 패턴을 체크, 숫자를 조절하여 메세지생성 조건을 변경할 수 있다 (80% -> 20%)
PERCENT_EXP = re.compile('.*([8-9])([0-9])%.*', re.DOTALL)
# TODO : IP:PublicIpAddress -> IP:PrivateIpAddress 와 같이 내부IP 로 변경해서 사용할 수 있다
# TODO : setting instance run command and user name
SSH_MONITER_COMMAND = 'ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no -i {} {}@{} "df -h -x tmpfs -x devtmpfs -x proc -x sysfs -x fusectl -x debugfs -x securityfs -x devpts -x pstore -x cgroup -x binfmt_misc"'


"""
    Simple AWS EC2 instances Disk usage monitor script
    
    Usage : ./ec2_disk_usage.py --profile=foo --region=ap-northeast-2 --slack=https://..../xxx/yyy/zzz --pem=~/.ssh/foo.pem
    
    1. select EC2 instances list filtering for Tag..
    2. SSH access and cli execute (df -h)

"""
def main():
    SEND_MESSAGES.append('>>>>> Start Time : {}\n>>>>> Monitor server disk is starting.'.format(datetime.datetime.now()))

    boto_client = BotoUtils(AwsService.EC2, GLOBAL_PARAMETER['aws_profile'], GLOBAL_PARAMETER['aws_region']).get_client()
    result_instances = boto_client.describe_instances(Filters=[{'Name': 'tag:Monitor', 'Values': ['target']}])

    if len(result_instances['Reservations']) == 0:
        SEND_MESSAGES.append('  >>>>> NotFound Target EC2 instances')
        return

    for r in result_instances['Reservations'][0]['Instances']:
        instance_user_name = 'ubuntu'
        if r['BlockDeviceMappings'][0]['DeviceName'].startswith('/dev/xvd'):
            instance_user_name = 'ec2-user'
        instance_ip = r['PublicIpAddress']
        instance_name = CommonUtils.find_json_kv_query(r['Tags'], 'Name')

        try:
            df_result = ScriptUtils.run_awscli(SSH_MONITER_COMMAND.format(GLOBAL_PARAMETER['pem'], instance_user_name, instance_ip), False)
        except:
            print(traceback.format_exc())
            df_result = ''

        if df_result and PERCENT_EXP.match(df_result):
            SEND_MESSAGES.append('  >>>>> Instance : [{}-{}]'.format(instance_name, instance_ip))
            SEND_MESSAGES.append(df_result)
            SLACK_OPTIONS_PARAMETER['is_send'] = True


if __name__ == "__main__":
    try:
        main()
    except:
        print(traceback.format_exc())
    finally:
        print('\n'.join(SEND_MESSAGES))
        if SLACK_OPTIONS_PARAMETER['is_send']:
            SlackWebHooks.post_slack('\n'.join(SEND_MESSAGES), 'Scheduler', SLACK_OPTIONS_PARAMETER['color'])