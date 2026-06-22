from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct

class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create an S3 Bucket to hold the built React app
        site_bucket = s3.Bucket(self, "KaiznBonsaiFrontendBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Create a CloudFront Distribution referencing the S3 bucket
        distribution = cloudfront.Distribution(self, "KaiznBonsaiDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
            ),
            default_root_object="index.html",
            # SPA Support: Redirect 404 to index.html
            error_responses=[cloudfront.ErrorResponse(
                http_status=404,
                response_page_path="/index.html",
                response_http_status=200
            )]
        )

        CfnOutput(self, "FrontendBucketName",
            value=site_bucket.bucket_name,
            description="The S3 bucket name for frontend assets"
        )

        CfnOutput(self, "CloudFrontDistributionId",
            value=distribution.distribution_id,
            description="The CloudFront Distribution ID"
        )

        CfnOutput(self, "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="URL for the frontend distribution"
        )
