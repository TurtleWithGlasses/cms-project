from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..schemas import UserCreate, UserResponse
from ..models import User
from ..database import get_db
from ..auth import hash_password, verify_password, create_access_token
from datetime import timedelta
from ..config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

# User registration route
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists in the database by email or username
    existing_user = db.query(User).filter((User.email == user.email) | (User.username == user.username)).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Hash the password
    hashed_password = hash_password(user.password)  # Corrected to hash_password
    
    # Create the new user object
    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    
    # Add and commit the new user to the database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user": {"id": new_user.id, "username": new_user.username, "email": new_user.email}}

# Login and token creation route
@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
