from django.urls import path

from . import views

urlpatterns = [
    # ex: /drpapp/ - the index page
    path("", views.comparison, name="comparison"),
]
