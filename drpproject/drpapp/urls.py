from django.urls import path

from . import views

urlpatterns = [
    # ex: /drpapp/ - the index page
    path("", views.index, name="index"),
    
    # ex: /drpapp/comparison/ - the price comparison page
    path("comparison/", views.comparison, name="comparison"),
    
    # ex: /drpapp/diet/ - the dietary preferences page
    path("diet/", views.diet, name="diet"),
    
    # ex: /drpapp/recommendations/ - the recipe recommendations page
    path("recommendations/", views.recommendations, name="recommendations"),

    path("proxy_tesco_basket/", views.proxy_tesco_basket, name="proxy_tesco_basket"),
]
