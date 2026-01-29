# admin.py - Version corrigée (sans duplication de payment_status)

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ProductCategory, Product, Service, TemplateCategory,
    DocumentTemplate, TrainingCourse, Inquiry, BasketItem,
    Order, OrderItem, Registration
)

# Configuration de l'admin site
admin.site.site_header = 'Global Business Consulting Admin'
admin.site.site_title = 'Administration'
admin.site.index_title = 'Tableau de bord'


# Inline pour OrderItem
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_type', 'product_id', 'name', 'price', 'quantity', 'total')
    can_delete = False

    def total(self, obj):
        return f"{obj.total} €"

    total.short_description = 'Total'


# Product Category Admin
@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'icon')
    list_editable = ('display_order',)
    search_fields = ('name',)
    ordering = ('display_order', 'name')


# Product Admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'industry', 'price', 'is_active', 'created_at')
    list_filter = ('category', 'industry', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'features')
    list_editable = ('price', 'is_active')
    readonly_fields = ('created_at', 'updated_at', 'slug')
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'slug', 'category', 'industry', 'description')
        }),
        ('Prix et disponibilité', {
            'fields': ('price', 'is_active', 'image')
        }),
        ('Caractéristiques', {
            'fields': ('features', 'specifications'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Service Admin
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_type', 'duration', 'price_range', 'is_active')
    list_filter = ('service_type', 'is_active')
    search_fields = ('name', 'description', 'features')
    list_editable = ('is_active', 'price_range')
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'service_type', 'description')
        }),
        ('Détails', {
            'fields': ('duration', 'price_range')
        }),
        ('Caractéristiques', {
            'fields': ('features', 'target_audience'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
    )


# Template Category Admin
@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'icon')
    list_editable = ('display_order',)
    search_fields = ('name',)
    ordering = ('display_order', 'name')


# Document Template Admin
@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'format', 'price', 'pages', 'is_popular', 'last_updated')
    list_filter = ('category', 'format', 'is_popular', 'last_updated')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_popular')
    readonly_fields = ('last_updated', 'slug')
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Détails du template', {
            'fields': ('format', 'price', 'pages', 'file_size', 'version')
        }),
        ('Statut', {
            'fields': ('is_popular',)
        }),
        ('Métadonnées', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )


# Training Course Admin
@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration', 'level', 'price', 'is_certified', 'is_active', 'created_at')
    list_filter = ('level', 'is_certified', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'syllabus')
    list_editable = ('price', 'is_active')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'description', 'duration', 'level')
        }),
        ('Prix et certification', {
            'fields': ('price', 'is_certified')
        }),
        ('Contenu', {
            'fields': ('syllabus', 'requirements'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# Basket Item Admin
@admin.register(BasketItem)
class BasketItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'price', 'quantity', 'total_display', 'session_short', 'added_at')
    list_filter = ('product_type', 'added_at')
    search_fields = ('name', 'session_key')
    readonly_fields = ('added_at',)

    def session_short(self, obj):
        return obj.session_key[:20] + '...' if len(obj.session_key) > 20 else obj.session_key

    session_short.short_description = 'Session'

    def total_display(self, obj):
        return f"{obj.total} €"

    total_display.short_description = 'Total'

    def has_add_permission(self, request):
        return False  # Empêche l'ajout manuel d'articles au panier


# Order Admin - CORRIGÉ (payment_status enlevé de la première fieldsets)
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'customer_email', 'total', 'status', 'payment_status',
                    'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'shipping_method')
    search_fields = ('order_number', 'customer_name', 'customer_email', 'customer_phone')
    readonly_fields = ('created_at', 'updated_at', 'order_number', 'session_key')
    inlines = [OrderItemInline]
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']

    fieldsets = (
        ('Informations commande', {
            'fields': ('order_number', 'session_key', 'status')
        }),
        ('Informations client', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_company')
        }),
        ('Détails financiers', {
            'fields': ('subtotal', 'shipping', 'tax', 'total')
        }),
        ('Livraison', {
            'fields': ('shipping_method', 'shipping_address')
        }),
        ('Paiement', {
            'fields': ('payment_method', 'payment_status')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, f"{queryset.count()} commande(s) marquée(s) comme 'en traitement'")

    mark_as_processing.short_description = "Marquer comme en traitement"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, f"{queryset.count()} commande(s) marquée(s) comme 'expédiée(s)'")

    mark_as_shipped.short_description = "Marquer comme expédié"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, f"{queryset.count()} commande(s) marquée(s) comme 'livrée(s)'")

    mark_as_delivered.short_description = "Marquer comme livré"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f"{queryset.count()} commande(s) marquée(s) comme 'annulée(s)'")

    mark_as_cancelled.short_description = "Marquer comme annulé"


# Order Item Admin
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'name', 'product_type', 'price', 'quantity', 'total_display')
    list_filter = ('product_type',)
    search_fields = ('name', 'order__order_number')
    readonly_fields = ('order',)

    def order_number(self, obj):
        return obj.order.order_number

    order_number.short_description = 'N° Commande'

    def total_display(self, obj):
        return f"{obj.total} €"

    total_display.short_description = 'Total'

    def has_add_permission(self, request):
        return False  # Les items de commande sont créés automatiquement


# Inquiry Admin
@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'subject', 'status', 'created_at', 'industry')
    list_filter = ('status', 'created_at', 'industry')
    search_fields = ('full_name', 'email', 'company', 'subject', 'message')
    readonly_fields = ('created_at',)
    list_editable = ('status',)
    actions = ['mark_as_contacted', 'mark_as_in_progress', 'mark_as_closed']

    fieldsets = (
        ('Informations contact', {
            'fields': ('full_name', 'email', 'phone', 'company', 'industry')
        }),
        ('Demande', {
            'fields': ('subject', 'message')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def mark_as_contacted(self, request, queryset):
        queryset.update(status='contacted')
        self.message_user(request, f"{queryset.count()} demande(s) marquée(s) comme 'contactée(s)'")

    mark_as_contacted.short_description = "Marquer comme contacté"

    def mark_as_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
        self.message_user(request, f"{queryset.count()} demande(s) marquée(s) comme 'en cours'")

    mark_as_in_progress.short_description = "Marquer comme en cours"

    def mark_as_closed(self, request, queryset):
        queryset.update(status='closed')
        self.message_user(request, f"{queryset.count()} demande(s) marquée(s) comme 'fermée(s)'")

    mark_as_closed.short_description = "Marquer comme fermé"


# Registration Admin
@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'company', 'industry', 'formation', 'session_date', 'terms_accepted',
                    'created_at')
    list_filter = ('industry', 'formation', 'terms_accepted', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'company', 'phone')
    readonly_fields = ('created_at', 'password')
    list_editable = ('formation', 'session_date')

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    full_name.short_description = 'Nom complet'

    fieldsets = (
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'password')
        }),
        ('Informations professionnelles', {
            'fields': ('company', 'industry')
        }),
        ('Formation', {
            'fields': ('formation', 'session_date')
        }),
        ('Conditions', {
            'fields': ('terms_accepted',)
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    # Masquer le mot de passe en clair dans l'affichage
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:  # Si on édite un objet existant
            readonly_fields.append('password')
        return readonly_fields