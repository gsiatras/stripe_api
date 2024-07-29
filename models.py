from pydantic import BaseModel

class SubscriptionRequest(BaseModel):
    subscription_type: str  # 'standard' or 'custom'
    user_email: str
    price: float = 1