from django.contrib import admin
from django.urls import path

import proxy.views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('get_chunk', proxy.views.get_chunk, name='get_chunk'),
]
