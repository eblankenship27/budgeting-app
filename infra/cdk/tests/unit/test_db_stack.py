import aws_cdk as cdk
import pytest

from aws_cdk.assertions import Match, Template

from stacks.db_stack import DbStack

@pytest.fixture(scope="module")
def template() -> Template:
    app = cdk.App()
    return Template.from_stack(DbStack(app, "TestDb"))

def test_no_nat_or_internet_gateway(template:Template) -> None:
    template.resource_count_is("AWS::EC2::NatGateway", 0)
    template.resource_count_is("AWS::EC2::InternetGateway", 0)
    
def test_two_isolated_subnets(template: Template) -> None:
    template.resource_count_is("AWS::EC2::Subnet", 2)
    template.all_resources_properties("AWS::EC2::Subnet", {"MapPublicIpOnLaunch": False})
    
def test_cluster_cost_and_security_settings(template: Template) -> None:
    template.has_resource_properties(
        "AWS::RDS::DBCluster",
        {
            "Engine": "aurora-postgresql",
            "ServerlessV2ScalingConfiguration": {"MinCapacity": 0, "MaxCapacity": 1},
            "StorageEncrypted": True,
            "EnableIAMDatabaseAuthentication": True,
        },
    )

def test_cluster_deleted_without_snapshot(template: Template) -> None:
    template.has_resource(
        "AWS::RDS::DBCluster",
        {"DeletionPolicy": "Delete", "UpdateReplacePolicy": "Delete"},
    )
    
def test_database_grants_no_access_itself(template: Template) -> None:
    template.has_resource_properties(
        "AWS::EC2::SecurityGroup",
        {"GroupDescription": "RDS security group", "SecurityGroupIngress": Match.absent()}
    )
    template.resource_count_is("AWS::EC2::SecurityGroupIngress", 0)