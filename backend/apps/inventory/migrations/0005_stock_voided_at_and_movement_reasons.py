from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_stockmovement'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalstock',
            name='voided_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='stock',
            name='voided_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='stockmovement',
            name='reason',
            field=models.CharField(
                choices=[
                    ('RECEIPT', 'Receipt'),
                    ('SALE', 'Sale'),
                    ('RETURN', 'Return'),
                    ('ADJUSTMENT', 'Adjustment'),
                    ('VOID', 'Void'),
                    ('RECEIPT_REVERSAL', 'Receipt reversal'),
                ],
                max_length=20,
            ),
        ),
    ]
