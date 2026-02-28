from fastapi import APIRouter, Depends, HTTPException, status
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from pydantic import BaseModel

from Chatbot.core.config import settings
from Chatbot.core.database import get_db
from Chatbot.models.user import User
from Chatbot.core.security import create_access_token

router = APIRouter()

class GoogleToken(BaseModel):
    token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

@router.post("/google", response_model=TokenResponse)
def google_auth(token_data: GoogleToken, db: Session = Depends(get_db)):
    try:
        # Verify the Google token
        idinfo = id_token.verify_oauth2_token(
            token_data.token, requests.Request(), settings.GOOGLE_CLIENT_ID
        )

        email = idinfo.get('email')
        name = idinfo.get('name')
        picture = idinfo.get('picture')

        if not email:
            raise HTTPException(status_code=400, detail="Invalid Google token: no email")

        # Check if user exists in DB
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Create a new user
            user = User(email=email, full_name=name, picture=picture)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Generate internal JWT
        access_token = create_access_token(data={"sub": user.email, "id": user.id})
        return {"access_token": access_token, "token_type": "bearer"}

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )
