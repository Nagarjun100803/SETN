from fastapi import APIRouter, Depends, Request, Response, Form, status
from config import templates
import schemas, utils, oauth2
from database import execute_sql_select_statement, execute_sql_commands
from fastapi.responses import RedirectResponse
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from config import get_user
from utils import serializer
from mail import send_reset_password_email
from itsdangerous.exc import SignatureExpired, BadSignature



router = APIRouter(tags = ["Users"])




@router.get("/index")
def get_index_page(
    request: Request,
    user: schemas.TokenData = Depends(oauth2.get_current_user)
):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@router.get("/signup")
def get_signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@router.get("/signin")
def get_signin_page(request: Request):
    return templates.TemplateResponse("signin.html", {"request": request})

@router.get("/forget_password")
def get_forget_password_page(request: Request): 
    return templates.TemplateResponse("forget_password.html", {"request": request})


@router.get("/reset_password")
def get_password_reset_page(request: Request, token: str):
    
    try:
        # Load the payload to verify the data.
        payload: dict = serializer.loads(token, max_age = 900) # Token valid for 15 mins.
        # print(payload)
    except BadSignature:
        return RedirectResponse("/forget_password", status_code = status.HTTP_307_TEMPORARY_REDIRECT)

    except SignatureExpired: # If the signature/token expired. Redirect the response to forget_password to make new request.
        return RedirectResponse("/forget_password", status_code = status.HTTP_307_TEMPORARY_REDIRECT)
    
    user = get_user("email_id", payload['email_id'])
    # Check whether the email id found in our db to avoid fake request. 
    if not user:
        return RedirectResponse("/forget_password", status_code = 404)
    
    return templates.TemplateResponse("reset_password.html", {"request": request})




@router.post("/signup")
def create_new_user(
    request: Request, response: Response,
    user_info: schemas.UserCreate = Form()
):
    
    if user_info.password != user_info.confirm_password: # Need to change this logic in client side.
        return templates.TemplateResponse("signup.html", {
            'request': request, 'error_message': 'Password and Confirm password not matched.!',
            'email_id': user_info.email_id, 'username': user_info.username
        }, status_code = 400)

    sql: str = """select * from users where email_id = %(email_id)s;"""
    previous_record = execute_sql_select_statement(sql, {'email_id': user_info.email_id}, fetch_all = False)
    
    # If user already found with the email id, return a error message.
    if previous_record:
        return templates.TemplateResponse("signup.html", {
            'request': request, 'error_message': 'Email already exixts!',
            'email_id': user_info.email_id, 'username': user_info.username
         }, status_code = 302)

    
    user_info.password = utils.get_hash_password(user_info.password) # Get a hashed password.

    sql: str = """
        insert into users
            (email_id, username, password, role)
        values
            (%(email_id)s, %(username)s, %(password)s, %(role)s)
        returning *
        ;
    """
    vars = user_info.model_dump(exclude = {'confirm_password'})
    
    new_user: None = execute_sql_commands(sql, vars)  # Create a new user.

    return RedirectResponse('/signin', status_code = status.HTTP_302_FOUND)

 

@router.post("/signin")
def authenticate_user(
    request: Request, response: Response,
    user_credentials: OAuth2PasswordRequestForm = Depends()
):
    context: dict = {"request": request, "username": user_credentials.username}

    # Get the user associated with the given email_id.
    user = get_user(by = 'email_id', value = user_credentials.username)
     
    if not user:
        context.update({"error_message": "No user found with this email!"})
        return templates.TemplateResponse("signin.html", context)
    
    if not utils.verify_password(user_credentials.password, user['password']):
        context.update({"error_message": "Invalid Password!"})
        return templates.TemplateResponse("signin.html", context, status_code = status.HTTP_401_UNAUTHORIZED)

    # Create access token.
    access_token: str = oauth2.create_access_token({"id": user["id"], "role": user["role"]})

    response = RedirectResponse('/index', status.HTTP_302_FOUND)
    # Save the token using set_cookie(), this save the piece of data 
    # in the client browser. The data is fetched every time to authenticate the user.
    response.set_cookie(
        key="access_token", value = f"Bearer {access_token}",
        path="/", httponly=True
    )

    return response



@router.post("/signout")
def signout(request: Request, response: Response):

    # Delete the token by using delete_cookie(). so the token ia no longer present
    # in the browser, The user need to enter the details again to access the app.
    response.delete_cookie(
        key = "access_token",
        path = "/",
        httponly = True    
        )

    return RedirectResponse("/index", status_code = 302, headers = response.headers)


@router.post("/forget_password")
def request_reset_password(
    request: Request, response: Response,
    password_reset_schema: schemas.PasswordResetRequesetSchema = Form()
):
    user = get_user('email_id', value = password_reset_schema.email_id)
    context: dict = {"request": request, "email_id": password_reset_schema.email_id}
    
    if not user:
        context.update({"error_message": "No user found with this email!"})
        return templates.TemplateResponse("forget_password.html", context)
    
    email_id: str = user['email_id']
    token: str = serializer.dumps({"email_id": email_id})
    
    # print(f"The token is {token}")

    # Sending the password reset email.
    send_reset_password_email(token, email_id)

    context.update({"sucess_message": "Check your email"})
    
    return templates.TemplateResponse("forget_password.html", context)
    


@router.post("/reset_password")
def reset_user_password(
    request: Request, response: Response,
    token: str,
    password_reset_schema: schemas.PasswordResetSchema = Form()
):
    context: dict = {"request": request}

    payload: dict = serializer.loads(token)
    
    email_id = payload["email_id"]
    
    if password_reset_schema.new_password != password_reset_schema.confirm_new_password:
        context.update({"error_message": "Password and confirm password not matched!"})
        return templates.TemplateResponse("reset_password.html", context)
    
    # Password reset operation.
    new_password = utils.get_hash_password(password_reset_schema.new_password) # Get a hashed version of password.
    sql: str = """
        update users set password = %(new_password)s where email_id = %(email_id)s returning *;
    """
    values = {"new_password": new_password, "email_id": email_id}

    updated_record: None = execute_sql_commands(sql, values)

    context.update({"sucess_message": "Password changed."})

    return templates.TemplateResponse("reset_password.html", context)



