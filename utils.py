import stripe

def get_existing_price(product_id: str, amount: int, currency: str = 'eur'):
    """
    Check if a price with the same amount and currency already exists for a given product.
    """
    prices = stripe.Price.list(product=product_id, limit=100)
    for price in prices:
        if price.unit_amount == amount and price.currency == currency:
            return price.id
    return None


def create_new_price(product_id: str, amount: int, currency: str = 'eur'):
    custom_price = stripe.Price.create(
                    unit_amount=amount,
                    currency=currency,
                    product=product_id,
                )
    return custom_price.id