from decimal import Decimal

from django.db import models


class Chunk(models.Model):
    lat = models.SmallIntegerField()
    lon = models.SmallIntegerField()

    expires_at = models.DateTimeField(null=True, blank=True, default=None)

    data = models.BinaryField()

    custom_data = models.BinaryField(null=True, blank=True, default=None)

    class Meta:
        unique_together = (('lat', 'lon'))
        index_together = (('lat', 'lon'))

    def __str__(self):
        return '{}, {}'.format(Decimal(self.lat) / 100, Decimal(self.lon) / 100)
