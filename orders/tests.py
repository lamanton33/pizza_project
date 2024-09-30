# tests.py

from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError


from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from .models import (
    Customer, DiscountCode, DeliveryPerson, Ingredient, Pizza,
    Drink, Dessert, Order, OrderItem, PostalCode
)

class CustomerModelTest(TestCase):
    def setUp(self):
        # Create a user and customer
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            first_name='John',
            last_name='Doe'
        )
        self.postal_code = PostalCode.objects.create(postal_code='12345')
        self.birthdate = date(1990, 1, 1)
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=self.birthdate,
            phone_number='1234567890',
            address='123 Test Street',
            postal_code=self.postal_code,
            gender='M',
        )

    def test_str_method(self):
        self.assertEqual(str(self.customer), 'John Doe')

    def test_check_birthday_reward(self):
        # When it's not the customer's birthday
        self.assertFalse(self.customer.check_birthday_reward())

        # Set the birthdate to today
        self.customer.birthdate = timezone.now().date()
        self.customer.birthday_reward_redeemed = False
        self.customer.save()
        self.assertTrue(self.customer.check_birthday_reward())

        # Reward already redeemed
        self.customer.redeem_birthday_reward()
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
        self.customer.total_pizzas_ordered = 9
        self.customer.save()
        self.assertFalse(self.customer.check_loyalty_discount())

        self.customer.total_pizzas_ordered = 10
        self.customer.save()
        self.assertTrue(self.customer.check_loyalty_discount())

    def test_reset_loyalty_discount(self):
        self.customer.total_pizzas_ordered = 15
        self.customer.save()
        self.customer.reset_loyalty_discount()
        self.assertEqual(self.customer.total_pizzas_ordered, 0)


class DiscountCodeModelTest(TestCase):
    def setUp(self):
        self.discount_code = DiscountCode.objects.create(
            code='DISCOUNT10',
            discount_percentage=Decimal('10.00'),
            is_redeemed=False
        )

    def test_str_method(self):
        self.assertEqual(str(self.discount_code), 'DISCOUNT10')

    def test_discount_code_redemption(self):
        self.assertFalse(self.discount_code.is_redeemed)
        self.discount_code.is_redeemed = True
        self.discount_code.save()
        self.assertTrue(self.discount_code.is_redeemed)


class DeliveryPersonModelTest(TestCase):
    def setUp(self):
        self.postal_code = PostalCode.objects.create(postal_code='12345')
        self.delivery_person = DeliveryPerson.objects.create(
            name='Delivery Guy',
            phone_number='0987654321',
            assigned_postal_code=self.postal_code
        )

    def test_str_method(self):
        self.assertEqual(str(self.delivery_person), 'Delivery Guy')

    def test_mark_unavailable(self):
        self.delivery_person.mark_unavailable()
        self.assertIsNotNone(self.delivery_person.unavailable_until)

    def test_is_available(self):
        # Initially available
        self.assertTrue(self.delivery_person.is_available())

        # Mark as unavailable
        self.delivery_person.mark_unavailable()
        self.assertFalse(self.delivery_person.is_available())

        # Simulate time passing
        self.delivery_person.unavailable_until = timezone.now() - timedelta(minutes=31)
        self.delivery_person.save()
        self.assertTrue(self.delivery_person.is_available())


class IngredientModelTest(TestCase):
    def setUp(self):
        self.ingredient = Ingredient.objects.create(
            name='Tomato',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )

    def test_str_method(self):
        self.assertEqual(str(self.ingredient), 'Tomato')


class PizzaModelTest(TestCase):
    def setUp(self):
        self.ingredient1 = Ingredient.objects.create(
            name='Tomato',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )
        self.ingredient2 = Ingredient.objects.create(
            name='Cheese',
            cost=Decimal('1.00'),
            is_vegan=False,
            is_vegetarian=True
        )
        self.pizza = Pizza.objects.create(name='Margherita')
        self.pizza.ingredients.add(self.ingredient1, self.ingredient2)

    def test_str_method(self):
        self.assertEqual(str(self.pizza), 'Margherita')

    def test_calculate_price(self):
        # Ingredient cost: 0.50 + 1.00 = 1.50
        # Profit margin: 1.50 * 0.40 = 0.60
        # Price before VAT: 1.50 + 0.60 = 2.10
        # VAT: 2.10 * 0.09 = 0.189
        # Total: 2.10 + 0.189 = 2.289
        # Rounded to 2 decimal places: 2.29
        self.assertEqual(self.pizza.calculate_price(), Decimal('2.29'))

    def test_is_vegan(self):
        self.assertFalse(self.pizza.is_vegan())

        # Remove non-vegan ingredient
        self.pizza.ingredients.remove(self.ingredient2)
        self.assertTrue(self.pizza.is_vegan())

    def test_is_vegetarian(self):
        self.assertTrue(self.pizza.is_vegetarian())

        # Add non-vegetarian ingredient
        meat = Ingredient.objects.create(
            name='Pepperoni',
            cost=Decimal('1.50'),
            is_vegan=False,
            is_vegetarian=False
        )
        self.pizza.ingredients.add(meat)
        self.assertFalse(self.pizza.is_vegetarian())


class OrderModelTest(TestCase):
    def setUp(self):
        # Create user and customer
        self.user = User.objects.create_user(
            username='customer1',
            password='pass123',
            first_name='Alice',
            last_name='Smith'
        )
        self.postal_code = PostalCode.objects.create(postal_code='54321')
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1985, 5, 15),
            phone_number='5551234567',
            address='456 Another St',
            postal_code=self.postal_code,
            gender='F',
            total_pizzas_ordered=10
        )

        # Create ingredients
        self.ingredient1 = Ingredient.objects.create(
            name='Tomato',
            cost=Decimal('0.50'),
            is_vegan=True,
            is_vegetarian=True
        )
        self.ingredient2 = Ingredient.objects.create(
            name='Cheese',
            cost=Decimal('1.00'),
            is_vegan=False,
            is_vegetarian=True
        )

        # Create pizza
        self.pizza = Pizza.objects.create(name='Margherita')
        self.pizza.ingredients.add(self.ingredient1, self.ingredient2)

        # Create order
        self.order = Order.objects.create(
            customer=self.customer,
            status='P',
        )

        # Create order item
        content_type = ContentType.objects.get_for_model(Pizza)
        self.order_item = OrderItem.objects.create(
            order=self.order,
            content_type=content_type,
            object_id=self.pizza.id,
            quantity=2
        )

    def test_str_method(self):
        self.assertEqual(str(self.order), f"Order #{self.order.id}")

    def test_get_total_before_discounts(self):
        total = self.order.get_total_before_discounts()
        expected_total = self.pizza.calculate_price() * 2
        self.assertEqual(total, expected_total)

    def test_apply_discount_loyalty(self):
        # Customer has ordered 10 pizzas, should get 10% discount
        self.order.apply_discount()
        total_before_discounts = self.order.get_total_before_discounts()
        expected_discount = (total_before_discounts * Decimal('0.10')).quantize(Decimal('0.01'))
        self.assertEqual(self.order.discount_applied, expected_discount)

        # Loyalty discount should reset
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.total_pizzas_ordered, 0)

    def test_apply_discount_code(self):
        # Create discount code
        discount_code = DiscountCode.objects.create(
            code='SAVE20',
            discount_percentage=Decimal('20.00'),
            is_redeemed=False
        )
        self.order.discount_code = discount_code
        self.order.apply_discount()

        total_before_discounts = self.order.get_total_before_discounts()

        # Calculate each discount separately and round
        discount_code_amount = (total_before_discounts * Decimal('0.20')).quantize(Decimal('0.01'))
        loyalty_discount_amount = (total_before_discounts * Decimal('0.10')).quantize(Decimal('0.01'))

        expected_discount = discount_code_amount + loyalty_discount_amount  # This should be 1.38

        # Verify the calculated expected_discount
        self.assertEqual(expected_discount, Decimal('1.38'))

        # Now assert that the actual discount applied matches the expected discount
        self.assertEqual(self.order.discount_applied, expected_discount)

        # Assert that the loyalty discount was reset
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.total_pizzas_ordered, 0)

        # Assert that the discount code was marked as redeemed
        discount_code.refresh_from_db()
        self.assertTrue(discount_code.is_redeemed)



    def test_apply_discount_birthday(self):
        # Set customer's birthday to today
        self.customer.birthdate = timezone.now().date()
        self.customer.birthday_reward_redeemed = False
        self.customer.save()

        self.order.apply_discount()
        total_before_discounts = self.order.get_total_before_discounts()
        self.assertEqual(self.order.discount_applied, total_before_discounts)

        # Birthday reward should be redeemed
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.birthday_reward_redeemed)

    def test_get_total_price(self):
        # Test without discounts
        total_before_discounts = self.order.get_total_before_discounts()
        self.order.discount_applied = Decimal('0.00')
        total_price = self.order.get_total_price()
        self.assertEqual(total_price, total_before_discounts)

        # Apply discount
        self.order.discount_applied = Decimal('5.00')
        total_price = self.order.get_total_price()
        self.assertEqual(total_price, total_before_discounts - Decimal('5.00'))

    def test_can_cancel(self):
        # Order just created, can cancel
        self.assertTrue(self.order.can_cancel())

        # Simulate order created over 5 minutes ago
        self.order.date = timezone.now() - timedelta(minutes=6)
        self.order.save()
        self.assertFalse(self.order.can_cancel())

    def test_cancel_order(self):
        self.order.cancel_order()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'C')

        # Cannot cancel after 5 minutes
        self.order.status = 'P'
        self.order.date = timezone.now() - timedelta(minutes=6)
        self.order.save()
        self.order.cancel_order()
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, 'C')

    def test_clean_order(self):
        # Remove all pizzas from order
        self.order.items.all().delete()
        with self.assertRaises(ValidationError):
            self.order.clean()

    def test_assign_delivery_person(self):
        # Create delivery person
        delivery_person = DeliveryPerson.objects.create(
            name='Deliverer',
            phone_number='5559876543',
            assigned_postal_code=self.postal_code
        )

        # Assign delivery person to order
        self.order.assign_delivery_person()
        self.order.refresh_from_db()
        self.assertEqual(self.order.delivery_person, delivery_person)

        # Delivery person should be marked unavailable
        delivery_person.refresh_from_db()
        self.assertIsNotNone(delivery_person.unavailable_until)

    def test_no_delivery_person_available(self):
        with self.assertRaises(ValidationError):
            self.order.assign_delivery_person()


class OrderItemModelTest(TestCase):
    def setUp(self):
        # Create user and customer
        self.user = User.objects.create_user(
            username='customer2',
            password='pass123',
            first_name='Bob',
            last_name='Brown'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            birthdate=date(1992, 8, 22),
            phone_number='5551112222',
            address='789 Some Rd',
            gender='M',
        )

        # Create drink
        self.drink = Drink.objects.create(
            name='Cola',
            price=Decimal('1.50')
        )

        # Create order
        self.order = Order.objects.create(
            customer=self.customer,
            status='P',
        )

        # Create order item for drink
        content_type = ContentType.objects.get_for_model(Drink)
        self.order_item = OrderItem.objects.create(
            order=self.order,
            content_type=content_type,
            object_id=self.drink.id,
            quantity=3
        )

    def test_get_total_price(self):
        total_price = self.order_item.get_total_price()
        expected_price = self.drink.price * 3
        self.assertEqual(total_price, expected_price)

    def test_str_method(self):
        self.assertEqual(str(self.order_item), f"3 x {self.drink.name}")
