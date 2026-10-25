from contextlib import asynccontextmanager

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status
)
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm
)
from pydantic import BaseModel, Field

from auth import (
    create_access_token,
    decode_access_token,
    verify_password
)
from database import (
    get_user,
    initialize_database
)
from guardrails import check_input
from rag import answer_question


# This runs once when FastAPI starts.
@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Secure Company RAG API",
    description=(
        "Authenticated internal company chatbot "
        "with RBAC and hybrid retrieval."
    ),
    version="1.0.0",
    lifespan=lifespan
)


# Tells FastAPI that clients obtain tokens from /token.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token"
)


# -------------------------------------------------
# Request and response models
# -------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    username: str
    role: str
    is_active: bool


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000
    )


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


# -------------------------------------------------
# Authentication helpers
# -------------------------------------------------

def authenticate_user(username, password):
    """
    Verifies the employee ID and password.

    Returns the database user when authentication succeeds.
    Returns None when authentication fails.
    """

    user = get_user(username)

    if user is None:
        return None

    if not user["is_active"]:
        return None

    if not verify_password(
        plain_password=password,
        stored_hash=user["password_hash"]
    ):
        return None

    return user


def get_current_user(
    token: str = Depends(oauth2_scheme)
):
    """
    Decodes the Bearer token and retrieves the current
    user from SQLite.
    """

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    username = decode_access_token(token)

    if username is None:
        raise credentials_error

    user = get_user(username)

    if user is None:
        raise credentials_error

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account is inactive."
        )

    return user


# -------------------------------------------------
# API endpoints
# -------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Secure Company RAG API is running."
    }


@app.post(
    "/token",
    response_model=TokenResponse
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticates an employee and returns a signed JWT.
    """

    user = authenticate_user(
        username=form_data.username,
        password=form_data.password
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect employee ID or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    access_token = create_access_token(
        username=user["username"]
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get(
    "/me",
    response_model=UserResponse
)
def read_current_user(
    current_user=Depends(get_current_user)
):
    """
    Returns the authenticated employee's account details.
    """

    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "is_active": bool(
            current_user["is_active"]
        )
    }


@app.post(
    "/chat",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest,
    current_user=Depends(get_current_user)
):
    """
    Answers a question using the role stored in SQLite.
    The client cannot select its own role.
    """

    question = request.question.strip()

    allowed, reason = check_input(question)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request blocked: {reason}"
        )

    try:
        answer, sources = answer_question(
            question=question,
            role=current_user["role"]
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error

    return {
        "answer": answer,
        "sources": sources
    }