import pathlib

from aws_cdk import (
    core,
    aws_apigateway,
    aws_lambda,
    aws_s3
)

from utils.cdk_utils import PythonS3CodeAsset


class BadgeManagerStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # get this files folder path
        path = pathlib.Path(__file__).parent.absolute()

        bucket = aws_s3.Bucket(
            scope=self,
            id="Bucket",
            public_read_access=True
        )

        badge_manager_handler = aws_lambda.Function(
            scope=self,
            id="Handler",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            retry_attempts=0,
            memory_size=1024,
            timeout=core.Duration.seconds(60),
            code=PythonS3CodeAsset(
                scope=self,
                id='HandlerCode',
                work_dir=str(path / 'badge_manager_lambda'),
                sources=['handler.py'],
                runtime=aws_lambda.Runtime.PYTHON_3_8),
            handler='handler.main',
            environment={'BADGE_MANAGER_BUCKET': bucket.bucket_name, 'REGION': self.region}
        )

        bucket.grant_read_write(identity=badge_manager_handler, objects_key_pattern="*.svg")

        api = aws_apigateway.LambdaRestApi(
            scope=self,
            id="Api",
            rest_api_name="BadgeManagerApi",
            handler=badge_manager_handler
        )

        api_key = api.add_api_key(id="ApiKey")

        api.add_usage_plan(
            id='UsagePlan',
            api_key=api_key,
            throttle=aws_apigateway.ThrottleSettings(burst_limit=2, rate_limit=10)
        )
