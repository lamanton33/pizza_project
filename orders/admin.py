from django.contrib import admin
#Register your models here

from .models import (
    Customer, Ingredient, Pizza, Drink, Dessert, 
    Order, OrderItem, DeliveryPerson, PostalCode, DiscountCode
)

admin.site.register(Customer)
admin.site.register(Ingredient)
admin.site.register(Pizza)
admin.site.register(Drink)
admin.site.register(Dessert)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(DeliveryPerson)
admin.site.register(PostalCode)
admin.site.register(DiscountCode)
