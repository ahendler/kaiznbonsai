from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Email is the primary login credential for a business-facing product.
    # username is retained for AbstractUser compatibility (createsuperuser, admin)
    # but is not exposed through the API surface.
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    # username is still required by createsuperuser; it is auto-populated on
    # programmatic creation via RegisterSerializer.
    REQUIRED_FIELDS = ["username"]
