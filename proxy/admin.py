from django.contrib import admin

from proxy.models import Chunk


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'lat', 'lon', 'expires_at')
    readonly_fields = ('lat', 'lon')
