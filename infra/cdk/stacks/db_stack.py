
import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk import custom_resources as cr
from constructs import Construct

CREATE_APP_USER = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'budgeting_app') THEN
        CREATE USER budgeting_app;
    END IF;
    GRANT rds_iam TO budgeting_app;
    GRANT USAGE, CREATE ON SCHEMA public TO budgeting_app;
END $$;
"""


class DbStack(cdk.Stack):
    
    def __init__(self, scope: Construct, construct_id: str, **kwrgs) -> None:
        super().__init__(scope, construct_id, **kwrgs)
        
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )
        
        self.cluster = rds.DatabaseCluster(
            self,
            "Cluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_13,
            ),
            writer=rds.ClusterInstance.serverless_v2("writer"),
            serverless_v2_min_capacity=0,
            serverless_v2_max_capacity=1,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            credentials=rds.Credentials.from_generated_secret("budgeting"),
            default_database_name="budgeting",
            iam_authentication=True,
            storage_encrypted=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            enable_data_api=True,
        )
    
        create_app_user = cr.AwsCustomResource(
            self,
            "CreateAppUser",
            on_create=cr.AwsSdkCall(
                service="rds-data",
                action="ExecuteStatement",
                parameters={
                    "resourceArn": self.cluster.cluster_arn,
                    "secretArn": self.cluster.secret.secret_arn,
                    "database": "budgeting",
                    "sql": CREATE_APP_USER,
                },
                physical_resource_id=cr.PhysicalResourceId.of("create-app-user"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(resources=[self.cluster.cluster_arn]),
            log_group=logs.LogGroup(
                self,
                "CreateAppUserLogs",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            ),
        )
        self.cluster.secret.grant_read(create_app_user)
        create_app_user.node.add_dependency(self.cluster)
        
        proxy_role = iam.Role(self, "ProxyRole", assumed_by=iam.ServicePrincipal("rds.amazonaws.com"))
        self.cluster.grant_connect(proxy_role, "budgeting_app")
        
        self.proxy = self.cluster.add_proxy(
            "Proxy",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            default_auth_scheme=rds.DefaultAuthScheme.IAM_AUTH,
            role=proxy_role,
        )
        
        # The validator's schema says DBProxyTargetGroup has no Tags, but the
        # CloudFormation reference lists Tags for it. Suppress just this rule here.
        cdk.Validations.of(self.proxy).acknowledge(
            cdk.Acknowledgment(
                id="CloudFormation-Validate::F3002",
                reason="Tags on DBProxyTargetGroup are valid per the CloudFormation docs; the validator schema is stale",
            ),
        )