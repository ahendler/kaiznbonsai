from django.db import models


class StockAllocationStrategy(models.TextChoices):
    FIFO = 'FIFO', 'First in, first out'
    FEFO = 'FEFO', 'First expired, first out'
