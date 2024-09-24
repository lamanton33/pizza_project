# tests.py

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError


from .models import (
    Customer, Pizza, Ingredient, Order, OrderItem,
    DiscountCode, Drink, Dessert, DeliveryPerson, PostalCode, EarningsReport
)

class CustomerModelTests(TestCase):
    def setUp(self):
        # Create a user and customer
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            first_name='Test',
            last_name='User'
        )
        self.birthdate = date(1990, 1, 1)
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=self.birthdate,
            phone_number='1234567890',
            address='123 Test St',
            gender='M'
        )

    def test_str_method(self):
        self.assertEqual(str(self.customer), 'Test User')

    def test_check_birthday_reward(self):
        # Test when it's not the customer's birthday
        self.assertFalse(self.customer.check_birthday_reward())

        # Set today to the customer's birthday
        today = date.today()
        self.customer.birthdate = today
        self.customer.birthday_reward_redeemed = False
        self.customer.save()

        self.assertTrue(self.customer.check_birthday_reward())

        # If reward is already redeemed
        self.customer.birthday_reward_redeemed = True
        self.customer.save()
        self.assertFalse(self.customer.check_birthday_reward())

    def test_redeem_birthday_reward(self):
        self.customer.redeem_birthday_reward()
        self.assertTrue(self.customer.birthday_reward_redeemed)

    def test_reset_birthday_reward(self):
        self.customer.birthday_reward_redeemed = True
        self.customer.save()
        self.customer.reset_birthday_reward()
        self.assertFalse(self.customer.birthday_reward_redeemed)

    def test_check_loyalty_discount(self):
        # Initially, total_pizzas_ordered is 0
        self.assertFalse(self.customer.check_loyalty_discount())

        # Set total_pizzas_ordered to 10
        self.customer.total_pizzas_ordered = 10
        self.customer.save()
        self.assertTrue(self.customer.check_loyalty_discount())

    def test_reset_loyalty_discount(self):
        self.customer.total_pizzas_ordered = 15
        self.customer.save()
        self.customer.reset_loyalty_discount()
        self.assertEqual(self.customer.total_pizzas_ordered, 0)

class IngredientModelTests(TestCase):
    def test_str_method(self):
        ingredient = Ingredient.objects.create(
            name='Tomato Sauce',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )
        self.assertEqual(str(ingredient), 'Tomato Sauce')

class PizzaModelTests(TestCase):
    def setUp(self):
        # Create ingredients
        self.tomato_sauce = Ingredient.objects.create(
            name='Tomato Sauce',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )
        self.cheese = Ingredient.objects.create(
            name='Cheese',
            cost=Decimal('1.00'),
            is_vegan=False,
            is_vegetarian=True
        )
        self.pepperoni = Ingredient.objects.create(
            name='Pepperoni',
            cost=Decimal('1.50'),
            is_vegan=False,
            is_vegetarian=False
        )
        # Create a pizza
        self.pizza = Pizza.objects.create(name='Pepperoni Pizza')
        self.pizza.ingredients.add(self.tomato_sauce, self.cheese, self.pepperoni)

    def test_str_method(self):
        self.assertEqual(str(self.pizza), 'Pepperoni Pizza')

    def test_calculate_price(self):
        # Calculate expected price
        ingredient_cost = self.tomato_sauce.cost + self.cheese.cost + self.pepperoni.cost
        profit_margin = (ingredient_cost * Decimal('0.40')).quantize(Decimal('0.01'))
        price_before_vat = ingredient_cost + profit_margin
        vat = (price_before_vat * Decimal('0.09')).quantize(Decimal('0.01'))
        total = (price_before_vat + vat).quantize(Decimal('0.01'))
        self.assertEqual(self.pizza.calculate_price(), total)

    def test_is_vegan(self):
        self.assertFalse(self.pizza.is_vegan())

        # Create a vegan pizza
        vegan_pizza = Pizza.objects.create(name='Vegan Pizza')
        vegan_pizza.ingredients.add(self.tomato_sauce)
        self.assertTrue(vegan_pizza.is_vegan())

    def test_is_vegetarian(self):
        self.assertFalse(self.pizza.is_vegetarian())

        # Create a vegetarian pizza
        vegetarian_pizza = Pizza.objects.create(name='Vegetarian Pizza')
        vegetarian_pizza.ingredients.add(self.tomato_sauce, self.cheese)
        self.assertTrue(vegetarian_pizza.is_vegetarian())

class OrderModelTests(TestCase):
    def setUp(self):
        # Create a user and customer
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            first_name='Test',
            last_name='User'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1990, 1, 1),
            phone_number='1234567890',
            address='123 Test St',
            gender='M',
            total_pizzas_ordered=10  # For loyalty discount
        )
        # Create ingredients
        self.tomato_sauce = Ingredient.objects.create(
            name='Tomato Sauce',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )
        self.cheese = Ingredient.objects.create(
            name='Cheese',
            cost=Decimal('1.00'),
            is_vegan=False,
            is_vegetarian=True
        )
        # Create a pizza
        self.pizza = Pizza.objects.create(name='Cheese Pizza')
        self.pizza.ingredients.add(self.tomato_sauce, self.cheese)
        # Create an order
        self.order = Order.objects.create(customer=self.customer)
        self.pizza_content_type = ContentType.objects.get_for_model(Pizza)
        self.order_item = OrderItem.objects.create(
            order=self.order,
            content_type=self.pizza_content_type,
            object_id=self.pizza.id,
            quantity=1
        )

    def test_get_total_before_discounts(self):
        total_before_discounts = self.order.get_total_before_discounts()
        expected_total = self.order_item.get_total_price()
        self.assertEqual(total_before_discounts, expected_total)

    def test_apply_discount(self):
        # Apply discounts
        self.order.apply_discount()
        # Since customer has ordered 10 pizzas, they should get a loyalty discount of 10%
        total_before_discounts = self.order.get_total_before_discounts()
        expected_discount = (total_before_discounts * Decimal('0.10')).quantize(Decimal('0.01'))
        self.assertEqual(self.order.discount_applied, expected_discount)
        # Customer's total_pizzas_ordered should be reset to 0
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.total_pizzas_ordered, 0)

    def test_get_total_price(self):
        self.order.apply_discount()
        total_price = self.order.get_total_price()
        total_before_discounts = self.order.get_total_before_discounts()
        expected_total = total_before_discounts - self.order.discount_applied
        self.assertEqual(total_price, expected_total)

    def test_clean(self):
        # Create an order without a pizza
        order_without_pizza = Order.objects.create(customer=self.customer)
        drink = Drink.objects.create(name='Cola', price=Decimal('1.00'))
        drink_content_type = ContentType.objects.get_for_model(Drink)
        OrderItem.objects.create(
            order=order_without_pizza,
            content_type=drink_content_type,
            object_id=drink.id,
            quantity=1
        )
        with self.assertRaises(ValidationError):
            order_without_pizza.clean()

    def test_can_cancel(self):
        self.assertTrue(self.order.can_cancel())
        # Simulate order created more than 5 minutes ago
        self.order.date = timezone.now() - timedelta(minutes=10)
        self.order.save()
        self.assertFalse(self.order.can_cancel())

    def test_cancel_order(self):
        self.order.cancel_order()
        self.assertEqual(self.order.status, 'C')
        # Test cannot cancel after 5 minutes
        self.order.status = 'P'
        self.order.date = timezone.now() - timedelta(minutes=10)
        self.order.save()
        self.order.cancel_order()
        self.assertNotEqual(self.order.status, 'C')

class OrderItemModelTests(TestCase):
    def setUp(self):
        # Create ingredients
        self.tomato_sauce = Ingredient.objects.create(
            name='Tomato Sauce',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )
        self.cheese = Ingredient.objects.create(
            name='Cheese',
            cost=Decimal('1.00'),
            is_vegan=False,
            is_vegetarian=True
        )
        # Create a pizza
        self.pizza = Pizza.objects.create(name='Cheese Pizza')
        self.pizza.ingredients.add(self.tomato_sauce, self.cheese)
        # Create a drink
        self.drink = Drink.objects.create(name='Cola', price=Decimal('1.00'))
        # Create a user and customer
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1990, 1, 1),
            phone_number='1234567890',
            address='123 Test St',
            gender='M'
        )
        # Create an order with the customer
        self.order = Order.objects.create(customer=self.customer)
        # Create order items
        self.pizza_content_type = ContentType.objects.get_for_model(Pizza)
        self.drink_content_type = ContentType.objects.get_for_model(Drink)
        self.pizza_order_item = OrderItem.objects.create(
            order=self.order,
            content_type=self.pizza_content_type,
            object_id=self.pizza.id,
            quantity=2
        )
        self.drink_order_item = OrderItem.objects.create(
            order=self.order,
            content_type=self.drink_content_type,
            object_id=self.drink.id,
            quantity=3
        )

    def setUp(self):
        # Create ingredients
        self.tomato_sauce = Ingredient.objects.create(
            name='Tomato Sauce',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )
        self.cheese = Ingredient.objects.create(
            name='Cheese',
            cost=Decimal('1.00'),
            is_vegan=False,
            is_vegetarian=True
        )
        # Create a pizza
        self.pizza = Pizza.objects.create(name='Cheese Pizza')
        self.pizza.ingredients.add(self.tomato_sauce, self.cheese)
        # Create a drink
        self.drink = Drink.objects.create(name='Cola', price=Decimal('1.00'))
        # Create an order
        self.order = Order.objects.create()
        # Create order items
        self.pizza_content_type = ContentType.objects.get_for_model(Pizza)
        self.drink_content_type = ContentType.objects.get_for_model(Drink)
        self.pizza_order_item = OrderItem.objects.create(
            order=self.order,
            content_type=self.pizza_content_type,
            object_id=self.pizza.id,
            quantity=2
        )
        self.drink_order_item = OrderItem.objects.create(
            order=self.order,
            content_type=self.drink_content_type,
            object_id=self.drink.id,
            quantity=3
        )

    def test_get_total_price_pizza(self):
        expected_total = self.pizza.calculate_price() * self.pizza_order_item.quantity
        self.assertEqual(self.pizza_order_item.get_total_price(), expected_total)

    def test_get_total_price_drink(self):
        expected_total = self.drink.price * self.drink_order_item.quantity
        self.assertEqual(self.drink_order_item.get_total_price(), expected_total)

class RegisterViewTests(TestCase):
    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_register_view_post_success(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password': 'newpass',
            'first_name': 'New',
            'last_name': 'User',
            'birthdate': '1990-01-01',
            'phone_number': '1234567890',
            'address': '123 New St',
            'gender': 'M'
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertTrue(Customer.objects.filter(user__username='newuser').exists())

    def test_register_view_post_existing_username(self):
        User.objects.create_user(username='existinguser', password='pass')
        response = self.client.post(reverse('register'), {
            'username': 'existinguser',
            'password': 'newpass',
            'first_name': 'New',
            'last_name': 'User',
            'birthdate': '1990-01-01',
            'phone_number': '1234567890',
            'address': '123 New St',
            'gender': 'M'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('register'))
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), 'Username already exists.')

class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_view_post_success(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass'
        })
        self.assertRedirects(response, reverse('place_order'))
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_view_post_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), 'Invalid login credentials')

class PlaceOrderViewTests(TestCase):
    def setUp(self):
        # Create a user and log in
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        # Create a customer
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1990, 1, 1),
            phone_number='1234567890',
            address='123 Test St',
            gender='M'
        )
        # Create ingredients
        self.tomato_sauce = Ingredient.objects.create(
            name='Tomato Sauce',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )
        self.cheese = Ingredient.objects.create(
            name='Cheese',
            cost=Decimal('1.00'),
            is_vegan=False,
            is_vegetarian=True
        )
        # Create a pizza
        self.pizza = Pizza.objects.create(name='Cheese Pizza')
        self.pizza.ingredients.add(self.tomato_sauce, self.cheese)
        # Create a drink
        self.drink = Drink.objects.create(name='Cola', price=Decimal('1.00'))
        # Create a dessert
        self.dessert = Dessert.objects.create(name='Cake', price=Decimal('2.00'))

    def test_place_order_get(self):
        response = self.client.get(reverse('place_order'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cheese Pizza')
        self.assertContains(response, 'Cola')
        self.assertContains(response, 'Cake')

    def test_place_order_post(self):
        response = self.client.post(reverse('place_order'), {
            'pizzas': [self.pizza.id],
            'drinks': [self.drink.id],
            'desserts': [self.dessert.id]
        })
        # Assuming 'order_confirmation' view uses order_id as parameter
        order = Order.objects.filter(customer=self.customer).first()
        self.assertRedirects(response, reverse('order_confirmation', args=[order.id]))
        # Check that order is created with items
        self.assertIsNotNone(order)
        self.assertEqual(order.items.count(), 3)
        # Check that total_pizzas_ordered is updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.total_pizzas_ordered, 1)

    def test_place_order_post_with_invalid_discount_code(self):
        response = self.client.post(reverse('place_order'), {
            'pizzas': [self.pizza.id],
            'discount_code': 'INVALIDCODE'
        })
        self.assertRedirects(response, reverse('place_order'))
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), 'Invalid discount code.')

class OrderConfirmationViewTests(TestCase):
    def setUp(self):
        # Create a user and log in
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        # Create a customer
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1990, 1, 1),
            phone_number='1234567890',
            address='123 Test St',
            gender='M'
        )

        # Create an order
        self.order = Order.objects.create(customer=self.customer)

    def test_order_confirmation_view(self):
        response = self.client.get(reverse('order_confirmation', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Order Number: {self.order.id}")


class OrderHistoryViewTests(TestCase):
    def setUp(self):
        # Create a user and log in
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        # Create a customer
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1990, 1, 1),
            phone_number='1234567890',
            address='123 Test St',
            gender='M'
        )
        # Create orders
        self.order1 = Order.objects.create(customer=self.customer)
        self.order2 = Order.objects.create(customer=self.customer)

    def test_order_history_view(self):
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Order #{self.order1.id}")
        self.assertContains(response, f"Order #{self.order2.id}")

class CancelOrderViewTests(TestCase):
    def setUp(self):
        # Create a user and log in
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        # Create a customer
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1990, 1, 1),
            phone_number='1234567890',
            address='123 Test St',
            gender='M'
        )
        # Create an order
        self.order = Order.objects.create(customer=self.customer)

    def test_cancel_order_within_time(self):
        response = self.client.get(reverse('cancel_order', args=[self.order.id]))
        self.assertRedirects(response, reverse('order_history'))
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), 'Order has been canceled successfully.')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'C')

    def test_cancel_order_past_time(self):
        # Simulate order created more than 5 minutes ago
        self.order.date = timezone.now() - timedelta(minutes=10)
        self.order.save()
        response = self.client.get(reverse('cancel_order', args=[self.order.id]))
        self.assertRedirects(response, reverse('order_history'))
        messages = list(response.wsgi_request._messages)
        self.assertEqual(str(messages[0]), 'You can no longer cancel this order.')
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, 'C')

class RestaurantMonitoringViewTests(TestCase):
    def setUp(self):
        # Create a staff user and log in
        self.staff_user = User.objects.create_user(username='staffuser', password='staffpass', is_staff=True)
        self.client.login(username='staffuser', password='staffpass')
        # Create a user and customer for the orders
        self.user = User.objects.create_user(username='customeruser', password='customerpass')
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1990, 1, 1),
            phone_number='1234567890',
            address='123 Customer St',
            gender='M'
        )
        # Create orders with different statuses and a customer
        self.order_p = Order.objects.create(status='P', customer=self.customer)
        self.order_i = Order.objects.create(status='I', customer=self.customer)
        self.order_o = Order.objects.create(status='O', customer=self.customer)
        self.order_d = Order.objects.create(status='D', customer=self.customer)

    def setUp(self):
        # Create a staff user and log in
        self.staff_user = User.objects.create_user(username='staffuser', password='staffpass', is_staff=True)
        self.client.login(username='staffuser', password='staffpass')
        # Create orders with different statuses
        self.order_p = Order.objects.create(status='P')
        self.order_i = Order.objects.create(status='I')
        self.order_o = Order.objects.create(status='O')
        self.order_d = Order.objects.create(status='D')

    def test_restaurant_monitoring_view(self):
        response = self.client.get(reverse('restaurant_monitoring'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Order #{self.order_p.id}")
        self.assertContains(response, f"Order #{self.order_i.id}")
        self.assertContains(response, f"Order #{self.order_o.id}")
        self.assertNotContains(response, f"Order #{self.order_d.id}")

# class EarningsReportViewTests(TestCase):
#     def setUp(self):
#         # Create a staff user and log in
#         self.staff_user = User.objects.create_user(username='staffuser', password='staffpass', is_staff=True)
#         self.client.login(username='staffuser', password='staffpass')
#         # Create earnings reports
#         self.report = EarningsReport.objects.create(
#             report_month=date(2021, 1, 1),
#             total_earnings=Decimal('1000.00'),
#             number_of_orders=50,
#             total_spent=Decimal('700.00'),
#             region='Test Region',
#             customer_gender='M',
#             customer_age_group='20-30'
#         )

#     def test_earnings_report_view(self):
#         response = self.client.get(reverse('earnings_report'))
#         self.assertEqual(response.status_code, 200)
#         self.assertContains(response, f"Earnings Report - {self.report.report_month}")
