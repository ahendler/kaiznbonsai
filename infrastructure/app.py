#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infrastructure.frontend_stack import FrontendStack
from infrastructure.backend_stack import BackendStack

app = cdk.App()

FrontendStack(app, "KaiznBonsaiFrontendStack")
BackendStack(app, "KaiznBonsaiBackendStack")

app.synth()
