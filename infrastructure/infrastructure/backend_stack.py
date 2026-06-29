import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from aws_cdk import (
    Stack,
    aws_elasticbeanstalk as elasticbeanstalk,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_s3_assets as s3_assets,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(
            f"Missing required environment variable: {name}. "
            f"Set it in infrastructure/.env (see infrastructure/.env.example)."
        )
    return value


class BackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        eb_instance_role = iam.Role(
            self,
            "EBInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        )
        eb_instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSElasticBeanstalkWebTier")
        )
        eb_instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSElasticBeanstalkMulticontainerDocker")
        )
        eb_instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly")
        )

        eb_instance_profile = iam.CfnInstanceProfile(
            self, "EBInstanceProfile", roles=[eb_instance_role.role_name]
        )

        backend_repo = ecr.Repository(
            self,
            "BackendRepo",
            repository_name="kaiznbonsai-backend",
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
        )

        CfnOutput(
            self,
            "KaiznBonsaiEcrRepoUri",
            value=backend_repo.repository_uri,
            description="The ECR Repository URI",
        )

        eb_deploy_bucket = s3.Bucket(
            self,
            "EBDeployBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        CfnOutput(
            self,
            "EBDeployBucketName",
            value=eb_deploy_bucket.bucket_name,
            description="S3 Bucket for EB application versions",
        )

        app = elasticbeanstalk.CfnApplication(
            self, "KaiznBonsaiEBApp", application_name="KaiznBonsaiApp"
        )

        backend_asset = s3_assets.Asset(self, "KaiznBonsaiBackendAsset", path="../backend")

        app_version = elasticbeanstalk.CfnApplicationVersion(
            self,
            "KaiznBonsaiAppVersion",
            application_name=app.application_name,
            source_bundle=elasticbeanstalk.CfnApplicationVersion.SourceBundleProperty(
                s3_bucket=backend_asset.s3_bucket_name,
                s3_key=backend_asset.s3_object_key,
            ),
        )
        app_version.add_dependency(app)

        env = elasticbeanstalk.CfnEnvironment(
            self,
            "KaiznBonsaiEBEnv",
            environment_name="KaiznBonsai-Prod",
            application_name=app.application_name,
            solution_stack_name="64bit Amazon Linux 2023 v4.13.2 running Docker",
            version_label=app_version.ref,
            option_settings=[
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:launchconfiguration",
                    option_name="IamInstanceProfile",
                    value=eb_instance_profile.ref,
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:launchconfiguration",
                    option_name="InstanceType",
                    value="t3.small",
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="SECRET_KEY",
                    value=_require_env("DJANGO_SECRET_KEY"),
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="DEBUG",
                    value="False",
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="CORS_ALLOWED_ORIGINS",
                    value=_require_env("CORS_ALLOWED_ORIGINS"),
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="POSTGRES_USER",
                    value=_require_env("POSTGRES_USER"),
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="POSTGRES_PASSWORD",
                    value=_require_env("DB_PASSWORD"),
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="POSTGRES_DB",
                    value=_require_env("POSTGRES_DB"),
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elb:healthcheck",
                    option_name="Target",
                    value="HTTP:80/admin/login/",
                ),
            ],
        )
        env.add_dependency(app_version)

        CfnOutput(
            self,
            "EBApplicationName",
            value=app.application_name,
            description="Elastic Beanstalk Application Name",
        )

        CfnOutput(
            self,
            "EBEnvironmentName",
            value=env.environment_name,
            description="Elastic Beanstalk Environment Name",
        )

        CfnOutput(
            self,
            "EBEnvironmentURL",
            value=env.attr_endpoint_url,
            description="URL of the Elastic Beanstalk Environment",
        )

        backend_cf = cloudfront.Distribution(
            self,
            "BackendCloudFront",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    env.attr_endpoint_url,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
        )

        CfnOutput(
            self,
            "BackendCloudFrontURL",
            value=f"https://{backend_cf.distribution_domain_name}",
            description="Secure HTTPS URL for the backend API (Use this as VITE_API_URL)",
        )
