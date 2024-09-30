from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q  # Add this import



class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birthdate = models.DateField()
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    postal_code = models.ForeignKey('PostalCode', on_delete=models.SET_NULL, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')], null=True)
    total_pizzas_ordered = models.PositiveIntegerField(default=0)
    birthday_reward_redeemed = models.BooleanField(default=False)


    def __str__(self):
        return self.user.get_full_name()
    
    def check_birthday_reward(self):
        today = timezone.now().date()
        if self.birthdate.month == today.month and self.birthdate.day == today.day:
            if not self.birthday_reward_redeemed:
                return True
        return False
    
    def redeem_birthday_reward(self):
        self.birthday_reward_redeemed = True
        self.save()

    def reset_birthday_reward(self):
        # Call this method at the start of a new day or year to reset the redemption status
        self.birthday_reward_redeemed = False
        self.save()
        
    def check_loyalty_discount(self):
        return self.total_pizzas_ordered >= 10
        
    def reset_loyalty_discount(self):
        self.total_pizzas_ordered = 0
        self.save()



# DiscountCode model
class DiscountCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_redeemed = models.BooleanField(default=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.code

# DeliveryPerson model
class DeliveryPerson(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    assigned_postal_code = models.ForeignKey('PostalCode', on_delete=models.SET_NULL, null=True, blank=True)
    unavailable_until = models.DateTimeField(null=True, blank=True)

    def mark_unavailable(self):
        self.unavailable_until = timezone.now() + timedelta(minutes=30)
        self.save()

    def is_available(self):
        if self.unavailable_until is None:
            return True
        if timezone.now() >= self.unavailable_until:
            # Reset availability
            self.unavailable_until = None
            self.save()
            return True
        return False

    def __str__(self):
        return self.name
class Ingredient(models.Model): 
    name = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=5, decimal_places=2)
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)

    def __str__(self):
        return self.name

# orders/models.py

# orders/models.py



class Pizza(models.Model):
    name = models.CharField(max_length=100)
    ingredients = models.ManyToManyField(Ingredient)

    def calculate_price(self):
        ingredient_cost = sum(ingredient.cost for ingredient in self.ingredients.all())
        profit_margin = (ingredient_cost * Decimal('0.40')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        price_before_vat = ingredient_cost + profit_margin
        vat = (price_before_vat * Decimal('0.09')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = price_before_vat + vat
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def is_vegan(self):
        return all(ingredient.is_vegan for ingredient in self.ingredients.all())

    def is_vegetarian(self):
        return all(ingredient.is_vegetarian for ingredient in self.ingredients.all())

    def __str__(self):
        return self.name

    name = models.CharField(max_length=100)
    ingredients = models.ManyToManyField(Ingredient)

    def calculate_price(self):
        ingredient_cost = sum(ingredient.cost for ingredient in self.ingredients.all())
        profit_margin = ingredient_cost * Decimal('0.40')  # Use Decimal for 40%
        price_before_vat = ingredient_cost + profit_margin
        vat = price_before_vat * Decimal('0.09') # Use Decimal for 9%
        return (price_before_vat + vat).quantize(Decimal('0.01'))

    def is_vegan(self):
        return all(ingredient.is_vegan for ingredient in self.ingredients.all())

    def is_vegetarian(self):
        return all(ingredient.is_vegetarian for ingredient in self.ingredients.all())

    def __str__(self):
        return self.name


class Drink(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return self.name

class Dessert(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=5, decimal_places=2)
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ('P', 'Being Prepared'),
        ('I', 'In Process'),
        ('O', 'Out for Delivery'),
        ('D', 'Delivered'),
        ('C', 'Cancelled'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    discount_applied = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P') #TODO write a method that would update status
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    delivery_person = models.ForeignKey(DeliveryPerson, on_delete=models.SET_NULL, null=True, blank=True)
    discount_code = models.ForeignKey(DiscountCode, on_delete=models.SET_NULL, null=True, blank=True)
    
 

    def get_total_before_discounts(self):
        total_before_discounts = sum(item.get_total_price() for item in self.items.all())
        return total_before_discounts
    


    def apply_discount(self):
        total_before_discounts = self.get_total_before_discounts()
        discount_amount = Decimal('0.00')

        # Apply discount code logic
        if self.discount_code and not self.discount_code.is_redeemed:
            discount_percentage = self.discount_code.discount_percentage / Decimal('100')
            discount_amount += (total_before_discounts * discount_percentage).quantize(Decimal('0.01'))
            self.discount_code.is_redeemed = True
            self.discount_code.save()

        # Apply loyalty discount (10% discount after 10 pizzas)
        if self.customer.check_loyalty_discount():
            discount_amount += (total_before_discounts * Decimal('0.10')).quantize(Decimal('0.01'))
            self.customer.reset_loyalty_discount()

        # Apply birthday reward (free pizza, set 100% discount)
        if self.customer.check_birthday_reward():
            discount_amount = total_before_discounts  # Full discount
            self.customer.redeem_birthday_reward()

        self.discount_applied = discount_amount
        self.save()

    def get_total_price(self):
        total_before_discounts= self.get_total_before_discounts()
        return total_before_discounts - self.discount_applied  # Subtract any discounts applied

    def assign_delivery_person(self):
        # Retrieve available delivery persons for the customer's postal code
        available_delivery_persons = DeliveryPerson.objects.filter(
            assigned_postal_code=self.customer.postal_code
        ).filter(
            models.Q(unavailable_until__isnull=True) | models.Q(unavailable_until__lte=timezone.now())
        )

        if not available_delivery_persons.exists():
            # Handle the case where no delivery persons are available
            raise ValidationError("No delivery persons are currently available for this area.")

        # Assign the first available delivery person
        self.delivery_person = available_delivery_persons.first()
        self.save()

        # Mark the assigned delivery person as unavailable for 30 minutes
        self.delivery_person.mark_unavailable()
    
    def clean(self):
        if not any(isinstance(item.item, Pizza) for item in self.items.all()):
            raise ValidationError('Each order must include at least one pizza.')
    
    def can_cancel(self):
        return (timezone.now() - self.date).total_seconds() < 300  # 5 minutes in seconds
    
    def cancel_order(self):
        if self.can_cancel():
            self.status = 'C'
            self.save()

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey('content_type', 'object_id')
    quantity = models.PositiveIntegerField(default=1)

    def get_total_price(self):
        if isinstance(self.item, Pizza):
            return self.item.calculate_price() * self.quantity
        else:
            return self.item.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"

 
    

# PostalCode model
class PostalCode(models.Model):
    postal_code = models.CharField(max_length=10)
    delivery_area_assignment = models.ForeignKey(DeliveryPerson, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivery_area_assignments')

    def __str__(self):
        return self.postal_code


# EarningsReport model
class EarningsReport(models.Model):
    report_month = models.DateField()
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_orders = models.IntegerField()
    total_spent = models.DecimalField(max_digits=10, decimal_places=2)
    region = models.CharField(max_length=100, null=True)
    customer_gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')], null=True)
    customer_age_group = models.CharField(max_length=20, null=True)

    def __str__(self):
        return f"Earnings Report - {self.report_month}"
