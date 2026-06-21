from django.db import models
from django.conf import settings

class TenantOwnedModel(models.Model):
    """
    Abstract base class that enforces tenant isolation by associating every
    record with a specific user. It also provides chronological sorting
    capabilities via created/updated timestamps.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # Do we want this? Business and compliance decision.
        related_name='%(class)ss' # e.g. user.products
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
