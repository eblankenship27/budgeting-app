from pathlib import Path
from platform import architecture

import aws_cdk as cdk
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from constructs import Construct

API_DIR = Path(__file__).resolve().parents[3] / "apps" / "api"

class ApiStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc = ec2.IVpc,
        cluster = rds.IDatabaseCluster,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        log_group = logs.LogGroup(
            self,
            "ApiLogs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        
        self.function = lambda_.DockerImageFunction(
            self,
            "ApiFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                str(API_DIR),
                platform=ecr_assets.Platform.LINUX_AMD64,
            ),
            architecture=lambda_.Architecture.X86_64,
            memory_size=512,
            timeout=cdk.Duration.seconds(30),
            # reserved_concurrent_executions=10, # (Account Limit currently doing its job, can request a raise later)
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            log_group=log_group,
            environment={
                "ENVIRONMENT": "dev",
                "DATABASE_URL": f"postgresql+psycopg://budgeting_app@{cluster.cluster_endpoint.hostname}:5432/budgeting",
            },
        )
        
        api = apigw.HttpApi(
            self,
            "HttpApi",
            default_integration=HttpLambdaIntegration("LambdaIntegration", self.function),
        )
        
        cdk.CfnOutput(self, "ApiUrl", value=api.api_endpoint)