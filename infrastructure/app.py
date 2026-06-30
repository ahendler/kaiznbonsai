#!/usr/bin/env python3
import aws_cdk as cdk

from infrastructure.backend_stack import BackendStack
from infrastructure.frontend_stack import FrontendStack

app = cdk.App()

# BackendStack must be instantiated first — it exposes eb_endpoint_url,
# which FrontendStack uses to add /api/* and /admin/* routing behaviors.
backend = BackendStack(app, "KaiznBonsaiBackendStack")
FrontendStack(app, "KaiznBonsaiFrontendStack", eb_endpoint_url=backend.eb_endpoint_url)

app.synth()
