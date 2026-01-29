from django.urls import path
from . import views

urlpatterns = [
    # Pages principales
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('products/', views.products, name='products'),
    path('trainings/', views.trainings, name='trainings'),
    path('documents/', views.documents, name='documents'),

    # Pages par industrie
    path('products/pharma/', views.pharma_industry, name='pharma_industry'),
    path('products/cosmetic/', views.cosmetic_industry, name='cosmetic_industry'),
    path('products/food/', views.food_industry, name='food_industry'),
    path('products/chemical/', views.chemical_industry, name='chemical_industry'),
    path('register/', views.register, name='register'),
    # Panier
    path('basket/', views.basket_view, name='basket'),
    path('add-to-basket/', views.add_to_basket, name='add_to_basket'),
    path('remove-basket-item/<int:item_id>/', views.remove_basket_item, name='remove_basket_item'),
    path('clear-basket/', views.clear_basket, name='clear_basket'),
    path('get-basket-count/', views.get_basket_count, name='get_basket_count'),

    # Checkout
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('download-invoice/<int:invoice_id>/', views.download_invoice, name='download_invoice'),



    # Formulaire
    path('inquiry/', views.submit_inquiry, name='inquiry'),
    path('contact/', views.contact_view, name='contact'),
]
