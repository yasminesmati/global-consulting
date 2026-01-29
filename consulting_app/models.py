# models.py - Version corrigée

from django.db import models
from django.utils.text import slugify


class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-box')
    display_order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Product Categories"
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class Product(models.Model):
    INDUSTRY_CHOICES = [
        ('pharma', 'Pharmaceutical'),
        ('cosmetic', 'Cosmetic'),
        ('food', 'Food & Beverage'),
        ('chemical', 'Chemical'),
        ('general', 'General'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    industry = models.CharField(max_length=20, choices=INDUSTRY_CHOICES)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    features = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Service(models.Model):
    SERVICE_TYPE_CHOICES = [
        ('training', 'Professional Training'),
        ('consulting', 'Consulting Service'),
        ('audit', 'Audit Service'),
        ('documentation', 'Documentation Service'),
        ('implementation', 'Implementation Service'),
    ]

    name = models.CharField(max_length=200)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES)
    description = models.TextField()
    duration = models.CharField(max_length=50, blank=True)
    price_range = models.CharField(max_length=100, blank=True)
    features = models.TextField(blank=True)
    target_audience = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"


class TemplateCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50)
    display_order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Template Categories"
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class DocumentTemplate(models.Model):
    FORMAT_CHOICES = [
        ('docx', 'Microsoft Word'),
        ('xlsx', 'Microsoft Excel'),
        ('pptx', 'Microsoft PowerPoint'),
        ('pdf', 'PDF'),
        ('zip', 'Bundle (ZIP)'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(TemplateCategory, on_delete=models.CASCADE, related_name='templates')
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    pages = models.IntegerField(default=1)
    file_size = models.CharField(max_length=20, blank=True)
    version = models.CharField(max_length=20, default='1.0')
    last_updated = models.DateField(auto_now=True)
    is_popular = models.BooleanField(default=False)

    class Meta:
        ordering = ['-last_updated', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TrainingCourse(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.CharField(max_length=50)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_certified = models.BooleanField(default=True)
    syllabus = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Inquiry(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    industry = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Inquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"Inquiry from {self.full_name} - {self.subject}"


class BasketItem(models.Model):
    PRODUCT_TYPES = [
        ('product', 'Product'),
        ('template', 'Document Template'),
        ('training', 'Training Course'),
        ('service', 'Service'),
    ]

    session_key = models.CharField(max_length=100, db_index=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    product_id = models.IntegerField()
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    image = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.name}"

    @property
    def total(self):
        return self.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En traitement'),
        ('shipped', 'Expédié'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    ]

    order_number = models.CharField(max_length=20, unique=True)
    session_key = models.CharField(max_length=100, db_index=True)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_company = models.CharField(max_length=200, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    shipping_method = models.CharField(max_length=50, default='digital')
    shipping_address = models.TextField(blank=True)
    payment_method = models.CharField(max_length=50, default='card')
    payment_status = models.CharField(max_length=20, default='pending')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande {self.order_number} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_type = models.CharField(max_length=20)
    product_id = models.IntegerField()
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.quantity}x {self.name}"

    @property
    def total(self):
        return self.price * self.quantity


class SimpleInvoice(models.Model):
    """Facture simplifiée"""
    invoice_number = models.CharField(max_length=50, unique=True)
    session_key = models.CharField(max_length=100)
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField()
    client_company = models.CharField(max_length=200, blank=True)
    client_address = models.TextField()
    client_city = models.CharField(max_length=100)
    client_country = models.CharField(max_length=100)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    items_json = models.TextField()  # Stocke les articles en JSON
    payment_method = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number

    @property
    def items(self):
        import json
        return json.loads(self.items_json)


class Registration(models.Model):
    FORMATION_CHOICES = [
        ('gmp', 'Formation GMP'),
        ('haccp', 'Formation HACCP'),
        ('reach', 'Formation REACH & CLP'),
        ('cosmetique', 'Réglementation Cosmétique'),
        ('webinaire', 'Webinaire Interactif'),
        ('classe-virtuelle', 'Classe Virtuelle'),
        ('sur-mesure', 'Formation Sur Mesure'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    industry = models.CharField(max_length=50)
    formation = models.CharField(max_length=50, choices=FORMATION_CHOICES, blank=True)
    session_date = models.CharField(max_length=50, blank=True)
    password = models.CharField(max_length=255)
    terms_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"
