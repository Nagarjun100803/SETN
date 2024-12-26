from fastapi.templating import Jinja2Templates
from typing import Literal
from psycopg2.extras import RealDictRow
from database import execute_sql_select_statement

templates = Jinja2Templates(directory = './templates')



def get_user(by: Literal['email_id', 'id'], value: str) -> RealDictRow | None :
    
    email_sql: str = "select * from users where email_id = %(email_id)s;"
    id_sql: str = "select * from users where id = %(id)s"

    if by == 'email_id':
        beneficiary = execute_sql_select_statement(email_sql, vars ={'email_id': value}, fetch_all = False)
    else:
        beneficiary = execute_sql_select_statement(id_sql, vars = {'id': value}, fetch_all = False)

    return beneficiary