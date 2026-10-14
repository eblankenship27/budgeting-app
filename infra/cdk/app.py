#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.api_stack import ApiStack
from stacks.auth_stack import AuthStack
from stacks.db_stack import DbStack


app = cdk.App()

env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
    region=os.getenv('CDK_DEFAULT_REGION')
)

db = DbStack(app, "BudgetingDbDev", env=env)

auth = AuthStack(app, "BudgetingAuthDev", env=env)

ApiStack(app, "BudgetingApiDev", env=env, vpc=db.vpc, db_proxy=db.proxy)

cdk.Tags.of(app).add("Project", "budgeting-app")
cdk.Tags.of(app).add("Environment", "dev")

app.synth()
