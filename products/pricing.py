"""
Price resolution helper.

Usage:
    from products.pricing import get_product_price

    price = get_product_price(product, organisation)
    # Returns a Decimal or None if the product has no price set.
"""

from .models import PriceBook, PriceBookEntry


def get_product_price(product, organisation=None):
    """
    Return the price_per_lm (Decimal) for *product* given *organisation*.

    Resolution order:
      1. Look in the organisation's own price book (if one is assigned).
      2. Fall back to the default price book.
      3. Return None if no price is found anywhere.

    This means a merchant's price book only needs entries for products
    where their price differs from the default — set up by exception.
    """
    # 1 — org-specific override
    if organisation is not None and organisation.price_book_id is not None:
        entry = (
            PriceBookEntry.objects
            .filter(price_book_id=organisation.price_book_id, product=product)
            .first()
        )
        if entry is not None:
            return entry.price_per_lm

    # 2 — default price book fallback
    default_book = PriceBook.get_default()
    if default_book is not None:
        entry = (
            PriceBookEntry.objects
            .filter(price_book=default_book, product=product)
            .first()
        )
        if entry is not None:
            return entry.price_per_lm

    # 3 — no price found
    return None
