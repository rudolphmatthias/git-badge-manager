#!/usr/bin/env python3

from aws_cdk import core

from badge_uploader_stack.badge_uploader_stack import BadgeUploaderStack


app = core.App()
BadgeUploaderStack(app, "git-badge-uploader", env={'region': 'us-east-1'})

app.synth()
