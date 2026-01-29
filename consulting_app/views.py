import pdfkit
from django.shortcuts import render
from django.template.loader import render_to_string

from .models import Inquiry, SimpleInvoice  # Assurez-vous que cet import est en haut du fichier
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect
from django.utils import timezone
import json
from .models import BasketItem, Product, DocumentTemplate, TrainingCourse, Service, Order, OrderItem
import uuid
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Sum  # AJOUTEZ CETTE LIGNE
from .models import DocumentTemplate, TemplateCategory  # AJOUTEZ CES IMPORTS

from django.db.models import Sum
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import json
import uuid
from .models import BasketItem, Order, OrderItem

def basket_view(request):
    """Affiche le panier - CORRECTION"""
    # 1. FORCER la création de session
    if not request.session.session_key:
        request.session.create()
        request.session.save()  # IMPORTANT: sauvegarder la session

    session_key = request.session.session_key
    print(f"🔍 DEBUG: Session key: {session_key}")

    # 2. Récupérer les articles AVEC session_key exacte
    basket_items = BasketItem.objects.filter(session_key=session_key)
    print(f"🔍 DEBUG: Articles trouvés: {basket_items.count()}")

    # 3. Afficher chaque article pour déboguer
    for item in basket_items:
        print(f"🔍 DEBUG: Article - ID:{item.id}, Nom:{item.name}, Prix:{item.price}, Qté:{item.quantity}")

    # 4. Si panier vide, créer un article de démo
    if not basket_items.exists():
        print("⚠️  Panier vide, création d'article démo...")
        demo_item = BasketItem.objects.create(
            session_key=session_key,
            product_type='template',
            product_id=999,
            name='Quality Manual Template (Démo)',
            price=Decimal('199.99'),
            quantity=1,
            description='Template de démonstration - Ajoutez des vrais articles depuis la page documents'
        )
        basket_items = BasketItem.objects.filter(session_key=session_key)

    # 5. Calcul des totaux
    subtotal = Decimal('0.00')
    item_count = 0

    for item in basket_items:
        try:
            item_total = item.price * Decimal(str(item.quantity))
            subtotal += item_total
            item_count += item.quantity
        except:
            subtotal += item.price * 1

    tax = subtotal * Decimal('0.20')
    shipping = Decimal('0.00')
    total = subtotal + tax + shipping

    print(f"📊 DEBUG: Sous-total: {subtotal}, TVA: {tax}, Total: {total}")

    # 6. Passer au template
    context = {
        'basket_items': basket_items,  # Les objets directement
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': total,
        'item_count': item_count,
    }

    return render(request, 'consulting_app/basket.html', context)


@require_POST
def add_to_basket(request):
    """Ajoute un article au panier - CORRIGÉ"""
    try:
        data = json.loads(request.body)
        product_type = data.get('product_type', 'template')
        product_id = data.get('product_id')

        print(f"🎯 DEBUG add_to_basket: type={product_type}, id={product_id}")

        # CRÉER la session si elle n'existe pas
        if not request.session.session_key:
            request.session.create()
            request.session.save()  # TRÈS IMPORTANT

        session_key = request.session.session_key
        print(f"🎯 DEBUG: Session key: {session_key}")

        # Chercher le produit dans la base
        product_name = "Template"
        product_price = Decimal('99.99')

        if product_type == 'template':
            try:
                template = DocumentTemplate.objects.get(id=product_id)
                product_name = template.name
                product_price = template.price
            except:
                product_name = f"Template #{product_id}"
                product_price = Decimal('99.99')

        # Vérifier si l'article existe déjà
        existing_item = BasketItem.objects.filter(
            session_key=session_key,
            product_type=product_type,
            product_id=product_id
        ).first()

        if existing_item:
            existing_item.quantity += 1
            existing_item.save()
            print(f"✅ Article existant mis à jour: {existing_item.name}")
        else:
            # Créer un nouvel article
            new_item = BasketItem.objects.create(
                session_key=session_key,
                product_type=product_type,
                product_id=product_id,
                name=product_name,
                price=product_price,
                quantity=1
            )
            print(f"✅ Nouvel article créé: {new_item.name}")

        # Compter les articles
        basket_count = BasketItem.objects.filter(
            session_key=session_key
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0

        print(f"📦 Total articles dans le panier: {basket_count}")

        return JsonResponse({
            'success': True,
            'message': 'Article ajouté!',
            'basket_count': basket_count
        })

    except Exception as e:
        print(f"❌ ERREUR add_to_basket: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_POST
def update_basket_item(request, item_id):
    """Met à jour la quantité d'un article"""
    try:
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))

        if quantity < 1:
            return JsonResponse({
                'success': False,
                'error': 'La quantité doit être au moins 1'
            })

        item = BasketItem.objects.get(id=item_id, session_key=request.session.session_key)
        item.quantity = quantity
        item.save()

        return JsonResponse({
            'success': True,
            'item_total': float(item.total),
            'item_price': float(item.price)
        })

    except BasketItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Article non trouvé'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_POST
def remove_basket_item(request, item_id):
    """Supprime un article du panier"""
    try:
        item = BasketItem.objects.get(id=item_id, session_key=request.session.session_key)
        item.delete()

        return JsonResponse({
            'success': True,
            'message': 'Article supprimé'
        })

    except BasketItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Article non trouvé'
        })


@require_POST
def clear_basket(request):
    """Vide complètement le panier"""
    try:
        BasketItem.objects.filter(session_key=request.session.session_key).delete()

        return JsonResponse({
            'success': True,
            'message': 'Panier vidé'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# Vue pour le checkout


def checkout_view(request):
    """Page de paiement simplifiée"""
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
    total = subtotal + tax

    # Si formulaire soumis, créer la facture
    if request.method == 'POST':
        try:
            # Préparer les données des articles pour JSON
            items_list = []
            for item in basket_items:
                items_list.append({
                    'name': item.name,
                    'price': str(item.price),
                    'quantity': item.quantity,
                    'total': str(item.total)
                })

            # Générer un numéro de facture
            invoice_number = f"FACT-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

            # Créer la facture
            invoice = SimpleInvoice.objects.create(
                invoice_number=invoice_number,
                session_key=session_key,
                client_name=f"{request.POST.get('first_name', '')} {request.POST.get('last_name', '')}",
                client_email=request.POST.get('email', ''),
                client_company=request.POST.get('company', ''),
                client_address=request.POST.get('address', ''),
                client_city=request.POST.get('city', ''),
                client_country=request.POST.get('country', 'FR'),
                subtotal=subtotal,
                tax=tax,
                total=total,
                items_json=json.dumps(items_list),
                payment_method=request.POST.get('payment_method', 'card')
            )

            # Vider le panier
            basket_items.delete()

            # Stocker l'ID de la facture dans la session
            request.session['last_invoice_id'] = invoice.id
            request.session.modified = True

            messages.success(request, f"Paiement réussi ! Facture {invoice_number} générée.")
            return redirect('payment_success')

        except Exception as e:
            print(f"Erreur: {str(e)}")
            messages.error(request, "Erreur lors du paiement")
            return redirect('checkout')

    # GET request - afficher le formulaire
    context = {
        'basket_items': basket_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
    }

    return render(request, 'consulting_app/checkout.html', context)


def payment_success(request):
    """Page de succès du paiement avec option de téléchargement"""
    invoice_id = request.session.get('last_invoice_id')

    if not invoice_id:
        messages.warning(request, "Aucune facture trouvée")
        return redirect('home')

    try:
        invoice = SimpleInvoice.objects.get(id=invoice_id)

        # Charger les articles depuis JSON
        items = invoice.items

        context = {
            'invoice': invoice,
            'items': items,
            'invoice_date': invoice.created_at,
        }

        return render(request, 'consulting_app/payment_success.html', context)

    except SimpleInvoice.DoesNotExist:
        messages.warning(request, "Facture introuvable")
        return redirect('home')


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