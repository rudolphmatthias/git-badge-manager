import os
import boto3
import json
from io import BytesIO
from pybadges import badge

BADGE_UPLOADER_BUCKET = os.environ['BADGE_UPLOADER_BUCKET']
REGION = os.environ['REGION']
s3_client = boto3.client('s3')


def main(event, context):
    body = json.loads(event['body'])
    total_coverage = body['total_coverage']
    project = body['project']
    branch = body['branch']

    # generate coverage badge
    if total_coverage >= 90:
        color = 'green'
    elif total_coverage >= 60:
        color = 'yellow'
    elif total_coverage >= 40:
        color = 'orange'
    else:
        color = 'red'

    svg_file_string = badge(left_text='coverage',
                            right_text=f'{total_coverage}%',
                            right_color=color,
                            logo='https://coverage.readthedocs.io/en/coverage-5.1/_static/sleepy-snake-circle-150.png',
                            embed_logo=True)

    # upload
    s3_client.upload_fileobj(Fileobj=BytesIO(svg_file_string.encode()),
                             Bucket=BADGE_UPLOADER_BUCKET,
                             Key=f"{project}/{branch}.svg")

    # output
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"url": f"https://s3.amazonaws.com/{BADGE_UPLOADER_BUCKET}/{project}/{branch}.svg"})
    }
