import json
import logging
import sys
import warnings
from unittest import TestCase

from aws_cdk import core
from badge_uploader_stack.badge_uploader_stack import BadgeUploaderStack


def get_template():
    app = core.App()
    BadgeUploaderStack(app, "badge-uploader")
    return json.dumps(app.synth().get_stack("badge-uploader").template)


class Tests(TestCase):

    def setUp(self) -> None:
        # False Alarm of ResourceWarning. Boto3 doesnt hold long living socket connections. Unittest falsely thinks so.
        logger = logging.getLogger()
        logger.level = logging.DEBUG
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-10s] (%(name)s): %(message)s"))
        logger.addHandler(stream_handler)

        log_handler = logging.getLogger('botocore')
        log_handler.setLevel('WARNING')
        log_handler = logging.getLogger('boto3')
        log_handler.setLevel('WARNING')
        log_handler = logging.getLogger('kmhelper')
        log_handler.setLevel('WARNING')
        log_handler = logging.getLogger('urllib3')
        log_handler.setLevel('WARNING')
        warnings.simplefilter("ignore", ResourceWarning)

    def test_sqs_queue_created(self):
        self.assertTrue("AWS::S3::Bucket" in get_template())
