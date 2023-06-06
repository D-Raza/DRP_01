from django.contrib import admin
from django.urls import include, path
from silk import urls as silk_urls

urlpatterns = [
    path("drpapp/", include("drpapp.urls")),
    path("admin/", admin.site.urls),
    path('silk/', include(silk_urls)),
]