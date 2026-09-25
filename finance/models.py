
from django.db import models


class Transaction(models.Model):

    transaction_id = models.CharField(
        max_length=20,
        unique=True
    )

    date = models.DateField()
    description = models.TextField()
    counterparty = models.CharField(max_length=255)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    method = models.CharField(max_length=100)

    category = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
    confidence = models.FloatField(null=True, blank=True)
    ai_reason = models.TextField(blank=True, default="")
    needs_review = models.BooleanField(default=True)

    ai_category = models.CharField(
    max_length=100,
    blank=True,
    default=""
    )

    

    def __str__(self):
        return self.transaction_id
