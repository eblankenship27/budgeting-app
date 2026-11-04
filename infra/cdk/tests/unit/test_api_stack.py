import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from stacks.api_stack import ApiStack
from stacks.db_stack import DbStack

@pytest.fixture(scope="module")
def template() -> Template:
    app = cdk.App()
    db = DbStack(app, "TestDb")
    return Template.from_stack(ApiStack(app, "TestApi", vpc=db.vpc, cluster=db.cluster))

def test_lambda_is_a_container_in_the_vpc(template: Template) -> None:
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "PackageType": "Image",
            "Architectures": ["x86_64"],
            "Timeout": 30,
            "VpcConfig": {"SubnetIds": Match.any_value()},
        },
    )
    
def test_one_http_api(template: Template) -> None:
    template.resource_count_is("AWS::ApiGatewayV2::Api", 1)
    
def test_logs_expire_and_are_destroyed(template: Template) -> None:
    template.has_resource_properties("AWS::Logs::LogGroup", {"RetentionInDays": 7})
    template.has_resource("AWS::Logs::LogGroup", {"DeletionPolicy": "Delete"})