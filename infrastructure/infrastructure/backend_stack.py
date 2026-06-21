import os
from aws_cdk import (
    Stack,
    aws_elasticbeanstalk as elasticbeanstalk,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_s3_assets as s3_assets,
    aws_s3 as s3,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct

class BackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. IAM Role for EB Instance Profile
        eb_instance_role = iam.Role(self, "EBInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        )
        eb_instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSElasticBeanstalkWebTier")
        )
        eb_instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSElasticBeanstalkMulticontainerDocker")
        )
        eb_instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSElasticBeanstalkMulticontainerDocker")
        )
        eb_instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly")
        )

        eb_instance_profile = iam.CfnInstanceProfile(self, "EBInstanceProfile",
            roles=[eb_instance_role.role_name]
        )

        # 2. Create an ECR Repository for the Backend image
        backend_repo = ecr.Repository(self, "BackendRepo",
            repository_name="kaiznbonsai-backend",
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True
        )

        CfnOutput(self, "KaiznBonsaiEcrRepoUri",
            value=backend_repo.repository_uri,
            description="The ECR Repository URI"
        )

        # 3. Create an S3 Bucket for GitHub Actions to upload EB source bundles
        eb_deploy_bucket = s3.Bucket(self, "EBDeployBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        CfnOutput(self, "EBDeployBucketName",
            value=eb_deploy_bucket.bucket_name,
            description="S3 Bucket for EB application versions"
        )

        # 4. Define the Elastic Beanstalk Application
        app = elasticbeanstalk.CfnApplication(self, "KaiznBonsaiEBApp",
            application_name="KaiznBonsaiApp"
        )

        # 3. Create the App Version by zipping the backend directory (including Dockerfile, eb-docker-compose.yml)
        # In a real pipeline, this zip should be pre-packaged and uploaded to S3.
        # Here we just point to the backend folder to let CDK package it as an S3 asset.
        backend_asset = s3_assets.Asset(self, "KaiznBonsaiBackendAsset",
            path="../backend"
        )

        app_version = elasticbeanstalk.CfnApplicationVersion(self, "KaiznBonsaiAppVersion",
            application_name=app.application_name,
            source_bundle=elasticbeanstalk.CfnApplicationVersion.SourceBundleProperty(
                s3_bucket=backend_asset.s3_bucket_name,
                s3_key=backend_asset.s3_object_key
            )
        )
        app_version.add_dependency(app)

        # 4. Define the Environment Configuration
        env = elasticbeanstalk.CfnEnvironment(self, "KaiznBonsaiEBEnv",
            environment_name="KaiznBonsai-Prod",
            application_name=app.application_name,
            solution_stack_name="64bit Amazon Linux 2023 v4.13.2 running Docker",
            version_label=app_version.ref,
            option_settings=[
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:launchconfiguration",
                    option_name="IamInstanceProfile",
                    value=eb_instance_profile.ref
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:autoscaling:launchconfiguration",
                    option_name="InstanceType",
                    value="t3.small" # Smallest instance that can comfortably run Django + Postgres containers
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="SECRET_KEY",
                    value="prod-secret-key-replace-me"
                ),
                elasticbeanstalk.CfnEnvironment.OptionSettingProperty(
                    namespace="aws:elasticbeanstalk:application:environment",
                    option_name="DEBUG",
                    value="False"
                ),
                # Note: Postgres configuration is internal to the docker-compose network on the instance,
                # but we could expose it via environment variables here if needed.
            ]
        )
        env.add_dependency(app_version)

        CfnOutput(self, "EBApplicationName",
            value=app.application_name,
            description="Elastic Beanstalk Application Name"
        )

        CfnOutput(self, "EBEnvironmentName",
            value=env.environment_name,
            description="Elastic Beanstalk Environment Name"
        )

        CfnOutput(self, "EBEnvironmentURL",
            value=env.attr_endpoint_url,
            description="URL of the Elastic Beanstalk Environment"
        )
