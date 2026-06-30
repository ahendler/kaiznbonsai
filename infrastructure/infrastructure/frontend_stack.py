from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class FrontendStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        eb_endpoint_url: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        site_bucket = s3.Bucket(
            self,
            "KaiznBonsaiFrontendBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # EB origin — used for /api/* and /admin/* path behaviors.
        # Caching is disabled and all methods/headers are forwarded so Django
        # receives the full request unchanged.
        eb_origin = origins.HttpOrigin(
            eb_endpoint_url,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        )

        eb_behavior = cloudfront.BehaviorOptions(
            origin=eb_origin,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
        )

        distribution = cloudfront.Distribution(
            self,
            "KaiznBonsaiDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                "/api/*": eb_behavior,
                "/admin/*": eb_behavior,
            },
            default_root_object="index.html",
            # SPA support: serve index.html for unknown paths so React Router
            # handles client-side navigation. Must not apply to /api/* paths —
            # CloudFront evaluates the most-specific behavior first, so the EB
            # behaviors above take precedence over this fallback.
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    response_http_status=200,
                )
            ],
        )

        CfnOutput(
            self,
            "FrontendBucketName",
            value=site_bucket.bucket_name,
            description="S3 bucket name for frontend assets",
        )

        CfnOutput(
            self,
            "CloudFrontDistributionId",
            value=distribution.distribution_id,
            description="CloudFront Distribution ID",
        )

        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="Live URL — frontend and API (/api/*) served from the same origin",
        )
