
from aws_cdk import cdk

class DbStack(cdk.stack):
    
    def __init__(self, scope: cdk.App, construct_id: str, **kwrgs) -> None:
        super().__init__(scope, construct_id, **kwrgs)
        
        vpc