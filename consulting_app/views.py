import json
import uuid
from datetime import datetime
from decimal import Decimal

import pdfkit
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Sum
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import BasketItem, Order, OrderItem
from .models import DocumentTemplate, TemplateCategory  # AJOUTEZ CES IMPORTS
from .models import Inquiry, SimpleInvoice  # Assurez-vous que cet import est en haut du fichier


@require_POST
@csrf_exempt
def add_to_basket(request):
    """Ajoute un article au panier - VERSION FONCTIONNELLE"""
    try:
        print("🎯 [ADD_TO_BASKET] Début")

        # FORCER la création de session si elle n'existe pas
        if not request.session.session_key:
            print("🔑 Création de nouvelle session")
            request.session.create()
            request.session.save()

        session_key = request.session.session_key
        print(f"🔑 Session ID: {session_key}")

        # Récupérer les données
        product_type = request.POST.get('product_type', 'template')
        product_id = request.POST.get('product_id', '1')

        print(f"📦 Produit: type={product_type}, id={product_id}")

        # Créer des données de test
        product_data = {
            'template': {
                'name': 'Template Qualité Premium',
                'price': Decimal('149.99'),
                'description': 'Template complet pour système de management qualité ISO 9001'
            },
            'service': {
                'name': 'Audit GMP Complète',
                'price': Decimal('999.99'),
                'description': 'Audit des bonnes pratiques de fabrication'
            },
            'training': {
                'name': 'Formation HACCP Avancée',
                'price': Decimal('299.99'),
                'description': 'Formation certifiante aux principes HACCP'
            }
        }

        # Sélectionner les données
        data = product_data.get(product_type, product_data['template'])

        # Vérifier si l'article existe déjà
        existing_item = BasketItem.objects.filter(
            session_key=session_key,
            product_type=product_type,
            product_id=product_id
        ).first()

        if existing_item:
            # Augmenter la quantité
            existing_item.quantity += 1
            existing_item.save()
            print(f"✅ Quantité augmentée: {existing_item.name}")
        else:
            # Créer un nouvel article
            BasketItem.objects.create(
                session_key=session_key,
                product_type=product_type,
                product_id=product_id,
                name=data['name'],
                price=data['price'],
                quantity=1,
                description=data['description']
            )
            print(f"✅ Nouvel article créé: {data['name']}")

        # Compter les articles
        basket_count = BasketItem.objects.filter(
            session_key=session_key
        ).aggregate(total=Sum('quantity'))['total'] or 0

        print(f"📊 Total panier: {basket_count} articles")
        print("🎯 [ADD_TO_BASKET] Fin - SUCCÈS")

        messages.success(request, f"✅ {data['name']} ajouté au panier !")
        return redirect('basket')

    except Exception as e:
        print(f"❌ [ADD_TO_BASKET] ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('basket')


def basket_view(request):
    """Affiche le panier - VERSION FONCTIONNELLE"""
    print("🛒 [BASKET_VIEW] Début")

    # FORCER la création de session
    if not request.session.session_key:
        print("🔑 Création session")
        request.session.create()
        request.session.save()

    session_key = request.session.session_key
    print(f"🔑 Session ID: {session_key}")

    # Récupérer les articles
    basket_items = BasketItem.objects.filter(session_key=session_key)
    print(f"📦 Articles trouvés: {basket_items.count()}")

    # Afficher chaque article (debug)
    for idx, item in enumerate(basket_items):
        print(f"  {idx + 1}. {item.name} x{item.quantity} = {item.price * item.quantity}€")

    # Calculer les totaux
    subtotal = Decimal('0.00')
    item_count = 0

    for item in basket_items:
        item_total = item.price * item.quantity
        subtotal += item_total
        item_count += item.quantity

    tax = subtotal * Decimal('0.20')
    total = subtotal + tax

    print(f"💰 Sous-total: {subtotal}€")
    print(f"💰 TVA: {tax}€")
    print(f"💰 Total: {total}€")
    print(f"📊 Nombre d'articles: {item_count}")
    print("🛒 [BASKET_VIEW] Fin")

    context = {
        'basket_items': basket_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'item_count': item_count,
    }

    return render(request, 'consulting_app/basket.html', context)


@require_POST
@csrf_exempt
def update_basket_item(request, item_id):
    """Met à jour la quantité d'un article"""
    try:
        print(f"🔄 [UPDATE_ITEM] ID: {item_id}")

        # Lire les données JSON
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))

        print(f"📈 Nouvelle quantité: {quantity}")

        # Trouver l'article
        try:
            item = BasketItem.objects.get(id=item_id)
            print(f"✅ Article trouvé: {item.name}")
        except BasketItem.DoesNotExist:
            print(f"❌ Article {item_id} non trouvé")
            return JsonResponse({
                'success': False,
                'error': 'Article non trouvé'
            })

        # Vérifier la session
        session_key = request.session.session_key
        if item.session_key != session_key:
            print("⚠️  Session différente")

        # Mettre à jour la quantité
        item.quantity = quantity
        item.save()
        print(f"✅ Quantité mise à jour")

        # Recalculer les totaux
        basket_items = BasketItem.objects.filter(session_key=item.session_key)
        subtotal = Decimal('0.00')
        item_count = 0

        for basket_item in basket_items:
            subtotal += basket_item.price * basket_item.quantity
            item_count += basket_item.quantity

        tax = subtotal * Decimal('0.20')
        total = subtotal + tax

        print(f"💰 Nouveaux totaux: sous-total={subtotal}, total={total}")

        return JsonResponse({
            'success': True,
            'item_total': float(item.price * item.quantity),
            'subtotal': float(subtotal),
            'tax': float(tax),
            'total': float(total),
            'item_count': item_count
        })

    except Exception as e:
        print(f"❌ [UPDATE_ITEM] ERREUR: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_POST
@csrf_exempt
def remove_basket_item(request, item_id):
    """Supprime un article du panier - VERSION FONCTIONNELLE"""
    try:
        print(f"🗑️ [REMOVE_ITEM] ID: {item_id}")

        # Vérifier la session
        if not request.session.session_key:
            print("❌ Pas de session")
            return JsonResponse({
                'success': False,
                'error': 'Pas de session active'
            })

        # Trouver l'article
        try:
            item = BasketItem.objects.get(id=item_id)
            print(f"✅ Article trouvé: {item.name}")
        except BasketItem.DoesNotExist:
            print(f"❌ Article {item_id} non trouvé")
            return JsonResponse({
                'success': False,
                'error': 'Article non trouvé'
            })

        # Vérifier que l'article appartient à la session
        session_key = request.session.session_key
        if item.session_key != session_key:
            print(f"⚠️  Session article: {item.session_key}")
            print(f"⚠️  Session requête: {session_key}")

        # Sauvegarder les infos avant suppression
        item_name = item.name
        item_session = item.session_key

        # Supprimer l'article
        item.delete()
        print(f"✅ Article '{item_name}' supprimé")

        # Recalculer les totaux
        basket_items = BasketItem.objects.filter(session_key=item_session)
        subtotal = Decimal('0.00')
        item_count = 0

        for basket_item in basket_items:
            subtotal += basket_item.price * basket_item.quantity
            item_count += basket_item.quantity

        tax = subtotal * Decimal('0.20')
        total = subtotal + tax

        print(f"💰 Nouveaux totaux: sous-total={subtotal}, total={total}")
        print(f"📊 Nombre d'articles restants: {item_count}")

        return JsonResponse({
            'success': True,
            'message': f'"{item_name}" supprimé',
            'subtotal': float(subtotal),
            'tax': float(tax),
            'total': float(total),
            'item_count': item_count
        })

    except Exception as e:
        print(f"❌ [REMOVE_ITEM] ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_POST
@csrf_exempt
def clear_basket(request):
    """Vide complètement le panier"""
    try:
        print("🧹 [CLEAR_BASKET] Début")

        # Vérifier la session
        if not request.session.session_key:
            print("❌ Pas de session")
            return JsonResponse({
                'success': False,
                'error': 'Pas de session active'
            })

        session_key = request.session.session_key
        print(f"🔑 Session ID: {session_key}")

        # Compter avant suppression
        item_count = BasketItem.objects.filter(session_key=session_key).count()
        print(f"🗑️  Articles à supprimer: {item_count}")

        # Supprimer tous les articles
        deleted_count, _ = BasketItem.objects.filter(session_key=session_key).delete()
        print(f"✅ {deleted_count} articles supprimés")

        return JsonResponse({
            'success': True,
            'message': f'{deleted_count} articles supprimés',
            'deleted_count': deleted_count
        })

    except Exception as e:
        print(f"❌ [CLEAR_BASKET] ERREUR: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def get_basket_count(request):
    """Retourne le nombre d'articles dans le panier"""
    try:
        print("🔢 [GET_BASKET_COUNT]")

        if not request.session.session_key:
            print("⚠️  Pas de session, retourne 0")
            return JsonResponse({'count': 0})

        session_key = request.session.session_key

        basket_count = BasketItem.objects.filter(
            session_key=session_key
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0

        print(f"📦 Compteur panier: {basket_count}")

        return JsonResponse({'count': basket_count})

    except Exception as e:
        print(f"❌ [GET_BASKET_COUNT] ERREUR: {str(e)}")
        return JsonResponse({'count': 0})


def checkout_view(request):
    """Page de paiement"""
    print("💳 [CHECKOUT_VIEW] Début")

    # Vérifier la session
    if not request.session.session_key:
        messages.warning(request, "Votre session a expiré")
        return redirect('basket')

    session_key = request.session.session_key
    basket_items = BasketItem.objects.filter(session_key=session_key)

    if not basket_items.exists():
        messages.warning(request, "Votre panier est vide")
        return redirect('basket')

    # Calculer les totaux
    subtotal = Decimal('0.00')
    for item in basket_items:
        subtotal += item.price * item.quantity

    tax = subtotal * Decimal('0.20')
    total = subtotal + tax

    # Si formulaire soumis
    if request.method == 'POST':
        try:
            print("💳 Traitement paiement...")

            # Créer un numéro de commande
            order_number = f"CMD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

            # Créer la commande
            order = Order.objects.create(
                order_number=order_number,
                session_key=session_key,
                customer_name=request.POST.get('name', 'Client'),
                customer_email=request.POST.get('email', ''),
                customer_phone=request.POST.get('phone', ''),
                customer_company=request.POST.get('company', ''),
                subtotal=subtotal,
                shipping=Decimal('0.00'),
                tax=tax,
                total=total,
                shipping_method='digital',
                payment_method=request.POST.get('payment_method', 'card'),
                payment_status='paid',
                status='processing'
            )

            # Créer les articles de commande
            for item in basket_items:
                OrderItem.objects.create(
                    order=order,
                    product_type=item.product_type,
                    product_id=item.product_id,
                    name=item.name,
                    price=item.price,
                    quantity=item.quantity
                )

            # Vider le panier
            basket_items.delete()

            # Stocker l'ID de la commande dans la session
            request.session['last_order_id'] = order.id
            request.session.modified = True

            print(f"✅ Commande créée: {order_number}")
            messages.success(request, f"Paiement réussi ! Commande #{order_number}")
            return redirect('payment_success')

        except Exception as e:
            print(f"❌ Erreur paiement: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f"Erreur: {str(e)}")
            return redirect('checkout')

    context = {
        'basket_items': basket_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
    }

    return render(request, 'consulting_app/checkout.html', context)


def payment_success(request):
    """Page de succès du paiement"""
    order_id = request.session.get('last_order_id')

    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            context = {'order': order}
        except Order.DoesNotExist:
            context = {'order': None}
    else:
        context = {'order': None}

    return render(request, 'consulting_app/payment_success.html', context)
def download_invoice(request, invoice_id):
    """Télécharger la facture en PDF"""
    try:
        invoice = SimpleInvoice.objects.get(id=invoice_id)
        items = invoice.items

        context = {
            'invoice': invoice,
            'items': items,
            'invoice_date': invoice.created_at,
            'company_name': 'Global Business Consulting',
            'company_address': '123 Rue du Commerce, 75000 Paris',
            'company_phone': '+33 1 23 45 67 89',
            'company_email': 'contact@global-consulting.com',
        }

        # Rendre le template HTML
        html_string = render_to_string('consulting_app/invoice_template.html', context)

        # Options pour PDF
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }

        # Générer le PDF
        pdf = pdfkit.from_string(html_string, False, options=options)

        # Retourner le PDF
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture-{invoice.invoice_number}.pdf"'
        return response

    except Exception as e:
        print(f"Erreur génération PDF: {str(e)}")
        messages.error(request, "Erreur lors de la génération du PDF")
        return redirect('payment_success')


def contact_view(request):
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            full_name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone', '')
            company = request.POST.get('company', '')
            subject = request.POST.get('service')
            message_text = request.POST.get('message')
            industry = request.POST.get('budget', '')

            # Créer une nouvelle entrée Inquiry
            inquiry = Inquiry.objects.create(
                full_name=full_name,
                email=email,
                phone=phone,
                company=company,
                subject=subject,
                message=message_text,
                industry=industry,
                status='new'
            )

            # Optionnel : Envoyer un email de notification
            if settings.EMAIL_HOST_USER:
                try:
                    # Email à l'administrateur
                    admin_subject = f"Nouveau message de contact : {subject}"
                    admin_message = f"""
                    Nouveau message de contact reçu :

                    Nom : {full_name}
                    Email : {email}
                    Téléphone : {phone}
                    Entreprise : {company}
                    Service : {subject}
                    Budget : {industry}

                    Message :
                    {message_text}

                    Statut : Nouveau
                    Date : {inquiry.created_at}
                    """

                    send_mail(
                        admin_subject,
                        admin_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.ADMIN_EMAIL],  # Remplacez par votre email
                        fail_silently=True,
                    )

                    # Email de confirmation à l'utilisateur
                    user_subject = "Confirmation de réception de votre message"
                    user_message = f"""
                    Cher(e) {full_name},

                    Nous avons bien reçu votre message et vous en remercions.

                    Voici un récapitulatif de votre demande :
                    Service : {subject}

                    Votre message :
                    {message_text}

                    Notre équipe vous répondra dans les plus brefs délais.

                    Cordialement,
                    L'équipe de Global Business Consulting
                    """

                    send_mail(
                        user_subject,
                        user_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=True,
                    )

                except Exception as e:
                    # Ne pas bloquer le processus si l'email échoue
                    print(f"Erreur d'envoi d'email : {e}")

            # Message de succès
            messages.success(request, 'Votre message a été envoyé avec succès ! Nous vous répondrons sous 24 heures.')

            # Rediriger vers la même page avec un message de succès
            return redirect('contact')

        except Exception as e:
            messages.error(request, f"Une erreur s'est produite : {str(e)}")
            return redirect('contact')

    # Pour les requêtes GET, afficher le formulaire vide
    return render(request, 'consulting_app/contact.html')

def home(request):
    return render(request, 'consulting_app/home.html')


def about(request):
    return render(request, 'consulting_app/about.html')


def products(request):
    """Page principale produits"""
    return render(request, 'consulting_app/products.html')


# Pages détaillées par industrie
def pharma_industry(request):
    context = {
        'title': 'Industrie Pharmaceutique',
        'icon': 'fas fa-pills',
        'description': 'Solutions complètes pour l\'industrie pharmaceutique',
        'services': [
            'Validation des processus GMP',
            'Qualification des équipements',
            'Documentation réglementaire',
            'Audits de conformité',
            'Formation du personnel'
        ],
        'products': [
            {'name': 'Logiciel GMP Pro', 'price': '2 500€/an', 'description': 'Gestion complète de la qualité'},
            {'name': 'Kit Validation', 'price': '850€', 'description': 'Templates et protocoles'},
            {'name': 'Formation FDA', 'price': '1 200€/personne', 'description': 'Certification internationale'},
        ],
        'certifications': ['FDA', 'EMA', 'GMP', 'ISO 13485']
    }
    return render(request, 'consulting_app/industry_detail.html', context)


def cosmetic_industry(request):
    context = {
        'title': 'Industrie Cosmétique',
        'icon': 'fas fa-spa',
        'description': 'Solutions pour les cosmétiques et produits de beauté',
        'services': [
            'Développement de PIF (Product Information File)',
            'Tests de sécurité et d\'efficacité',
            'Conformité règlementaire (Règlement Cosmétique EU)',
            'Étiquetage et packaging',
            'Audits fournisseurs'
        ],
        'products': [
            {'name': 'PIF Template Pro', 'price': '650€', 'description': 'Modèles complets de dossier produit'},
            {'name': 'Safety Assessment', 'price': '950€', 'description': 'Évaluation de sécurité'},
            {'name': 'Formulation Assistant', 'price': '1 500€', 'description': 'Logiciel de formulation'},
        ],
        'certifications': ['ISO 22716', 'GMP Cosmetics', 'Vegan Certified', 'Cruelty-Free']
    }
    return render(request, 'consulting_app/industry_detail.html', context)


def food_industry(request):
    context = {
        'title': 'Industrie Agroalimentaire',
        'icon': 'fas fa-utensils',
        'description': 'Solutions pour la sécurité et la qualité alimentaire',
        'services': [
            'Implémentation HACCP',
            'Traçabilité des produits',
            'Contrôle qualité',
            'Certifications bio et équitable',
            'Optimisation des processus'
        ],
        'products': [
            {'name': 'Système HACCP Pro', 'price': '1 800€',
             'description': 'Gestion complète de la sécurité alimentaire'},
            {'name': 'Traceability Software', 'price': '3 200€', 'description': 'Traçabilité en temps réel'},
            {'name': 'Formation Auditeur', 'price': '900€/personne', 'description': 'Certification auditeur interne'},
        ],
        'certifications': ['HACCP', 'ISO 22000', 'BRC', 'IFS', 'Bio']
    }
    return render(request, 'consulting_app/industry_detail.html', context)


def chemical_industry(request):
    context = {
        'title': 'Industrie Chimique',
        'icon': 'fas fa-flask',
        'description': 'Solutions pour la production et manipulation chimique',
        'services': [
            'Conformité REACH et CLP',
            'Sécurité des processus',
            'Gestion des déchets dangereux',
            'Analyse de risques',
            'Formation sécurité'
        ],
        'products': [
            {'name': 'REACH Compliance Suite', 'price': '2 800€', 'description': 'Gestion de la conformité REACH'},
            {'name': 'SDS Generator Pro', 'price': '1 200€', 'description': 'Générateur de fiches de sécurité'},
            {'name': 'Risk Assessment Tool', 'price': '1 500€', 'description': 'Analyse des risques chimiques'},
        ],
        'certifications': ['REACH', 'CLP', 'ISO 14001', 'OHSAS 18001']
    }
    return render(request, 'consulting_app/industry_detail.html', context)


def trainings(request):
    return render(request, 'consulting_app/trainings.html')


def documents(request):
    # Récupérer toutes les catégories de templates
    categories = TemplateCategory.objects.all().order_by('display_order')

    # Récupérer les templates par catégorie
    quality_templates = DocumentTemplate.objects.filter(
        category__name__icontains='quality'
    ).order_by('-is_popular', 'name')[:6]

    validation_templates = DocumentTemplate.objects.filter(
        category__name__icontains='validation'
    ).order_by('-is_popular', 'name')[:3]

    sops = DocumentTemplate.objects.filter(
        category__name__icontains='sop'
    ).order_by('-is_popular', 'name')[:5]

    # Préparer les données pour le template
    context = {
        'categories': categories,
        'quality_templates': [
            {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'price': template.price,
                'format': template.get_format_display(),
                'pages': template.pages,
                'industry': 'All',
                'icon': 'file-alt'
            } for template in quality_templates
        ],
        'validation_templates': [
            {
                'id': template.id,
                'name': template.name,
                'description': template.description[:100] + '...' if template.description else '',
                'price': template.price,
            } for template in validation_templates
        ],
        'sops': [
            {
                'id': template.id,
                'name': template.name,
                'industry': 'All',
                'format': template.get_format_display(),
                'price': template.price,
            } for template in sops
        ]
    }

    return render(request, 'consulting_app/documents.html', context)


def basket(request):
    return render(request, 'consulting_app/basket.html')


# ----- FONCTION POUR LE FORMULAIRE D'INQUIRY -----

def submit_inquiry(request):
    if request.method == 'POST':
        # Récupérer les données du formulaire
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        company = request.POST.get('company')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        industry = request.POST.get('industry')

        # Créer l'inquiry dans la base de données
        inquiry = Inquiry.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            company=company,
            subject=subject,
            message=message,
            industry=industry,
            status='new'  # Statut par défaut
        )

        return render(request, 'consulting_app/inquiry.html', {
            'success': True,
            'inquiry': inquiry  # Maintenant c'est un objet modèle
        })

    # Si GET, afficher le formulaire vide
    return render(request, 'consulting_app/inquiry.html', {'success': False})


@csrf_exempt  # AJOUTEZ CETTE LIGNE pour désactiver CSRF temporairement
def register(request):
    if request.method == 'POST':
        try:
            print("=== DÉBUT TRAITEMENT INSCRIPTION ===")  # Debug
            print("Données reçues:", request.POST)  # Debug

            # Vérifier si l'email existe déjà
            email = request.POST.get('email')
            print(f"Email: {email}")  # Debug

            # Vérifier si le modèle Registration existe
            try:
                from .models import Registration
                print("Modèle Registration importé avec succès")  # Debug

                if Registration.objects.filter(email=email).exists():
                    print("Email déjà utilisé")  # Debug
                    return JsonResponse({
                        'success': False,
                        'error': 'Cet email est déjà utilisé.'
                    })
            except Exception as e:
                print(f"Erreur avec le modèle Registration: {e}")  # Debug
                return JsonResponse({
                    'success': False,
                    'error': f'Erreur modèle: {str(e)}'
                })

            # Vérifier les mots de passe
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            print(f"Password: {password}, Confirm: {confirm_password}")  # Debug

            if password != confirm_password:
                return JsonResponse({
                    'success': False,
                    'error': 'Les mots de passe ne correspondent pas.'
                })

            if len(password) < 8:
                return JsonResponse({
                    'success': False,
                    'error': 'Le mot de passe doit contenir au moins 8 caractères.'
                })

            # Créer l'inscription
            print("Création de l'inscription...")  # Debug
            registration = Registration.objects.create(
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                email=email,
                phone=request.POST.get('phone', ''),
                company=request.POST.get('company', ''),
                industry=request.POST.get('industry'),
                formation=request.POST.get('formation', ''),
                session_date=request.POST.get('session_date', ''),
                password=password,
                terms_accepted=bool(request.POST.get('terms'))
            )

            print(f"Inscription créée avec ID: {registration.id}")  # Debug

            return JsonResponse({
                'success': True,
                'message': 'Inscription réussie !',
                'registration_id': registration.id
            })

        except Exception as e:
            print(f"=== ERREUR: {str(e)}")  # Debug
            import traceback
            traceback.print_exc()  # Affiche la trace complète

            return JsonResponse({
                'success': False,
                'error': f'Erreur serveur: {str(e)}'
            })

    # GET request - afficher le formulaire
    return render(request, 'consulting_app/register.html')




def get_basket_count(request):
    """Retourne le nombre d'articles dans le panier"""
    try:
        if not request.session.session_key:
            return JsonResponse({'count': 0})

        basket_count = BasketItem.objects.filter(
            session_key=request.session.session_key
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0

        return JsonResponse({'count': basket_count})
    except Exception as e:
        print(f"Error in get_basket_count: {e}")  # Debug
        return JsonResponse({'count': 0})

    @login_required
    def checkout_view(request):
        """Page de paiement"""
        # S'assurer qu'une session existe
        if not request.session.session_key:
            request.session.create()
            request.session.save()

        session_key = request.session.session_key
        basket_items = BasketItem.objects.filter(session_key=session_key)

        if not basket_items.exists():
            messages.warning(request, "Votre panier est vide")
            return redirect('basket')

        # Calculer les totaux
        subtotal = Decimal('0.00')
        for item in basket_items:
            subtotal += item.total

        tax = subtotal * Decimal('0.20')
        shipping = Decimal('0.00')
        total = subtotal + tax + shipping

        context = {
            'basket_items': basket_items,
            'subtotal': subtotal,
            'tax': tax,
            'shipping': shipping,
            'total': total,
        }

        return render(request, 'consulting_app/checkout.html', context)


def order_confirmation(request):
    """Page de confirmation de commande - Version simplifiée"""
    try:
        # S'assurer qu'une session existe
        if not request.session.session_key:
            messages.warning(request, "Session invalide")
            return redirect('home')

        session_key = request.session.session_key

        # Créer une commande factice pour l'affichage
        import uuid
        import random
        from decimal import Decimal

        # Générer un numéro de commande
        order_number = f"CMD{random.randint(1000, 9999)}-{str(uuid.uuid4())[:6].upper()}"

        # Récupérer la dernière commande de l'utilisateur
        last_order = Order.objects.filter(session_key=session_key).order_by('-created_at').first()

        if last_order:
            # Utiliser la dernière commande réelle
            order = last_order
            order_items = OrderItem.objects.filter(order=order)

            context = {
                'order': order,
                'order_items': order_items,
                'order_number': order.order_number,
                'order_date': order.created_at,
                'subtotal': order.subtotal,
                'tax': order.tax,
                'total': order.total,
            }
        else:
            # Créer un contexte factice
            context = {
                'order_number': order_number,
                'order_date': timezone.now(),
                'subtotal': Decimal('199.99'),
                'tax': Decimal('39.99'),
                'total': Decimal('239.98'),
            }

        return render(request, 'consulting_app/order_confirmation.html', context)

    except Exception as e:
        print(f"Erreur dans order_confirmation: {str(e)}")
        return redirect('home')