from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import stripe
import os
from dotenv import load_dotenv
from models import SubscriptionRequest
from utils import get_existing_price, create_new_price

app = FastAPI()

load_dotenv()

stripe.api_key = os.getenv('STRIPE_KEY')
standard_price_id = os.getenv('STANDARD_SUB_KEY')
custom_sub_id = os.getenv('CUSTOM_SUB_ID')
webhook_secret = os.getenv('WEBHOOK_KEY')

DOMAIN = "http://localhost:8000"

@app.post("/create-subscription")
async def create_subscription_session(request: SubscriptionRequest):
    """
    Creates a one-time payment or subscription checkout session with Stripe.

    This endpoint creates a Stripe Checkout Session based on the provided subscription request.
    For a 'standard' subscription type, it uses a predefined price ID. For a 'custom' subscription,
    it checks if a price exists for the given amount and creates a new one if needed.

    Parameters:
    - request (SubscriptionRequest): The subscription request containing the type, price, and user email.

    Returns:
    - dict: A dictionary containing the URL of the created checkout session.

    Raises:
    - HTTPException: If there is an error with Stripe or a general exception occurs.
    """
    try:
        if request.subscription_type == 'standard':
            price_id = standard_price_id
            sub_mode = 'subscription'
        elif request.subscription_type == 'custom':
            amount_in_cents = int(request.price * 100)  # Stripe expects the price in cents
            price_id = get_existing_price(custom_sub_id, amount_in_cents)

            if not price_id:
                # Create a new price for the custom product if it doesn't exist
                price_id = create_new_price(custom_sub_id, amount_in_cents)
            sub_mode = 'payment'
        else:
            raise ValueError("Invalid subscription type. Must be 'standard' or 'custom'.")

        # Create a checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                }
            ],
            mode=sub_mode,  # Mode set to 'payment' for one-time payments
            customer_email=request.user_email,  # Pre-fill the customer's email
            success_url=DOMAIN + '/success.html',
            cancel_url=DOMAIN + '/cancel.html',
            metadata={
                'user_email': request.user_email,
            }
        )

        return {"url": checkout_session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {e.user_message}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")


@app.post('/webhook')
async def webhook(request: Request):
    """
    Handles Stripe webhook events.

    This endpoint processes webhook events sent by Stripe. It verifies the event's authenticity,
    handles specific event types, and prints relevant information. Currently, it handles
    'payment_intent.succeeded' events.

    Parameters:
    - request (Request): The incoming HTTP request containing the webhook event payload and headers.

    Returns:
    - JSONResponse: A JSON response indicating success.

    Raises:
    - HTTPException: If the payload is invalid or the signature verification fails.
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        checkout_session = event['data']['object']  # contains a stripe.Checkout.Session
        customer_email = checkout_session.get('customer_email')
        # Define and call a function to handle the event checkout.session.completed
        print(f'Checkout session completed with email: {customer_email}')
    else:
        print('Unhandled event type {}'.format(event['type']))

    return JSONResponse({"success": True})

