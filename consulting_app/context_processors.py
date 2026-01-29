# consulting_app/context_processors.py
from .models import BasketItem
from django.db.models import Sum, F


def basket_context(request):
    """Ajoute les informations du panier à tous les templates"""
    basket_count = 0
    basket_total = 0

    if hasattr(request, 'session') and request.session.session_key:
        session_key = request.session.session_key
        basket_items = BasketItem.objects.filter(session_key=session_key)

        # Calculer le nombre d'articles
        basket_count = basket_items.aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0

        # Calculer le total
        basket_total = sum(item.total for item in basket_items)

    return {
        'basket_count': basket_count,
        'basket_total': basket_total,
    }