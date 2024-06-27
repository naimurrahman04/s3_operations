import subprocess as sp
import os
import argparse as ap
import json as js
from datetime import datetime
from tqdm import tqdm
import time

def x(cmd, task_name=""):
    try:
        with tqdm(total=100, desc=task_name, leave=True, ncols=100) as pbar:
            r = sp.run(cmd, check=True, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            o = r.stdout.decode('utf-8')
            pbar.update(100)
        print(o)
        return o
    except sp.CalledProcessError as e:
        eo = e.stderr.decode('utf-8')
        print(eo)
        return None

def u(fn, b, r, on=None):
    if on is None:
        on = os.path.basename(fn)
    cmd = f'aws s3 cp {fn} s3://{b}/{on} --region {r} --no-sign-request'
    return x(cmd, task_name="Uploading file...")

def d(b, on, r, fn=None):
    if fn is None:
        fn = os.path.basename(on)
    cmd = f'aws s3 cp s3://{b}/{on} {fn} --region {r} --no-sign-request'
    return x(cmd, task_name="Downloading file...")

def del_f(b, on, r):
    cmd = f'aws s3 rm s3://{b}/{on} --region {r} --no-sign-request'
    return x(cmd, task_name="Deleting file from S3...")

def s_to_s3(d, b, r):
    cmd = f'aws s3 sync {d} s3://{b}/ --region {r} --no-sign-request'
    return x(cmd, task_name="Syncing local directory to S3...")

def s_from_s3(b, d, r):
    cmd = f'aws s3 sync s3://{b}/ {d} --region {r} --no-sign-request'
    return x(cmd, task_name="Syncing S3 bucket to local directory...")

def check_s(b, r):
    results = {}

    acl_cmd = f'aws s3api get-bucket-acl --bucket {b} --region {r}'
    acl_out = x(acl_cmd, task_name="Checking bucket ACL...")
    results['ACL'] = acl_out

    if acl_out:
        acl = js.loads(acl_out)
        results['ACL'] = acl

    policy_cmd = f'aws s3api get-bucket-policy --bucket {b} --region {r}'
    policy_out = x(policy_cmd, task_name="Checking bucket policy...")
    results['Policy'] = policy_out

    if policy_out:
        policy = js.loads(policy_out)
        results['Policy'] = policy

    pab_cmd = f'aws s3api get-public-access-block --bucket {b} --region {r}'
    pab_out = x(pab_cmd, task_name="Checking public access block configuration...")
    results['PublicAccessBlock'] = pab_out

    if pab_out:
        pab_cfg = js.loads(pab_out)
        results['PublicAccessBlock'] = pab_cfg

    return results

def write_report(report_data, report_path):
    try:
        with open(report_path, 'w') as report_file:
            report_file.write("S3 Operations and Security Report\n")
            report_file.write(f"Generated on: {datetime.now()}\n\n")
            
            for section, data in report_data.items():
                report_file.write(f"=== {section} ===\n")
                if isinstance(data, dict):
                    report_file.write(js.dumps(data, indent=2))
                else:
                    report_file.write(data if data else "No data")
                report_file.write("\n\n")

        print(f"Report generated at {report_path}")
    except Exception as e:
        print(f"Failed to write report: {e}")

def m():
    try:
        p = ap.ArgumentParser(
            description='S3 Operations and Security Script',
            formatter_class=ap.ArgumentDefaultsHelpFormatter
        )
        p.add_argument('--directory', required=True, help='Path to the local directory to use for S3 operations.')
        p.add_argument('--bucket', required=True, help='Name of the S3 bucket to operate on.')
        p.add_argument('--region', required=True, help='AWS region where the S3 bucket is located.')
        p.add_argument('--report', required=True, help='Path to the report file.')

        a = p.parse_args()
        
        dp = a.directory
        bn = a.bucket
        rn = a.region
        rp = a.report

        report_data = {}

        if not os.path.isdir(dp):
            raise ValueError(f"The directory {dp} does not exist.")
        
        efp = os.path.join(dp, 'example.txt')
        if not os.path.isfile(efp):
            try:
                with open(efp, 'w') as f:
                    f.write("This is for test")
                print(f"Created example file {efp} with content 'This is for test'.")
            except Exception as e:
                print(f"Failed to create example file {efp}: {e}")
                return
        else:
            print(f"Example file {efp} already exists.")
        
        tasks = [
            ("Upload", lambda: u(efp, bn, rn)),
            ("Download", lambda: d(bn, 'example.txt', rn, os.path.join(dp, 'downloaded_example.txt'))),
            ("Delete", lambda: del_f(bn, 'example.txt', rn)),
            ("SyncToS3", lambda: s_to_s3(dp, bn, rn)),
            ("SyncFromS3", lambda: s_from_s3(bn, dp, rn)),
            ("SecurityCheck", lambda: check_s(bn, rn))
        ]

        for task_name, task_func in tasks:
            print(f"{task_name} in progress...")
            result = task_func()
            report_data[task_name] = result

        print("Generating report...")
        write_report(report_data, rp)
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    m()
