from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.security.oauth2 import OAuth2
from fastapi import HTTPException, Request, Security, status, Depends
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
import schemas
from utils import get_user
from config import settings



# EXPIRE_MINUTES = 100
# SECRET_KEY = 'shiva'
# ALGORIHM = 'HS256'



class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: str | None = None,
        scopes: dict[str, str] | None = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows = flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> str | None:
        authorization: str | None = request.cookies.get("access_token")

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_302_FOUND,
                    detail = "Not authorized",
                    headers = {"Location": "/signin"},
                )
            else:
                return None
        return param
    

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl='signin')


def create_access_token(payload: dict) -> str:

    new_payload = payload.copy()
    expiration = datetime.utcnow() + timedelta(minutes = settings.jwt_token_expire_minutes)
    new_payload.update({'exp': expiration})

    encoded_payload = jwt.encode(new_payload, key = settings.jwt_token_secret_key, algorithm = settings.jwt_token_algorithm)

    return encoded_payload



def get_current_user(token: str = Security(oauth2_scheme)) -> schemas.TokenData:
    try:
        payload = jwt.decode(token, settings.jwt_token_secret_key, algorithms=[settings.jwt_token_algorithm])
        user = get_user('id', value=payload.get('id'))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_302_FOUND,
                detail = "User not found",
                headers = {"Location": "/signin"},
            )
        
    except jwt.ExpiredSignatureError:
        # Redirect to sign-in page if token has expired
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail = "Your session expired, please login.",
            headers = {"Location": "/signin"},
        )
    
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail = "Invalid token",
            headers = {"Location": "/signin"},
        )
    
    return schemas.TokenData(id = user['id'], role = user['role'])



def get_current_beneficiary(user: schemas.TokenData = Depends(get_current_user)) -> schemas.TokenData:

    if user.role == "beneficiary":
        return user
    
    raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = 'You are not a beneficiary',
            headers = {"Location": "/index"}

    )


def get_current_admin(user: schemas.TokenData = Depends(get_current_user)) -> schemas.TokenData:

    if user.role == "admin":
        return user
    
    raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN, 
            detail = 'You are not an admin',
            headers = {"Location": "/index"}
    )
    

def get_current_volunteer(user: schemas.TokenData = Depends(get_current_user)) -> schemas.TokenData:

    if user.role == "volunteer":
        return user

    raise HTTPException(
        status_code = status.HTTP_403_FORBIDDEN, 
        detail = 'You are not a volunteer'
    )

def get_current_admin_or_volunteer(
    user: schemas.TokenData = Depends(get_current_user)
) -> schemas.TokenData:
    
    if (user.role == "admin") or (user.role == "volunteer"):
        return user 
    
    raise HTTPException(
        status_code = status.HTTP_403_FORBIDDEN,
        detail = "You are not an admin or volunteer." 
    )