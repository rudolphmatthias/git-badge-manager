#!/usr/bin/env python3

from aws_cdk import core

from badge_manager.badge_manager_stack import BadgeManagerStack


app = core.App()
BadgeManagerStack(app, "badge-manager", env={'region': 'us-east-1'})

app.synth()
