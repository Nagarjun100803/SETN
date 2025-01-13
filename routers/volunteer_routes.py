from typing import Literal
from fastapi import APIRouter, Request, status, Depends
from config import templates
import schemas
from oauth2 import get_current_volunteer
from database import execute_sql_select_statement


router = APIRouter(
    tags = ["Volunteer"],
    prefix = "/volunteer"
)


@router.get("/beneficiaries")
def get_test_page(
    request: Request,
    college_name: str = "",
    email_id: str = "",
    name: str = "",
    beneficiary_status: Literal["new", "all", "verified"] = "all",
    user: schemas.TokenData = Depends(get_current_volunteer)
):
    """
        This endpoint fetch the beneficiaries assigned by admin, 
        those beneficiaries are need to verify by logged-in volunteer.
    """

    sql: str = """
        select 
            per.id as id,
            ba.assigned_by,
            per.full_name as name,
            co.course,
            co.degree,
            co.department,
            edu.college_name,
            per.date_of_birth,
            per.aadhar_num,
            per.phone_num,
            u.email_id,
            per.is_verified
        from 
            beneficiary_assignments as ba
        join 
            beneficiary_personal_details as per
        on 
            ba.beneficiary_id = per.id
        join 
            beneficiary_educational_details as edu
        on 
            per.id = edu.id 
        join 
            courses as co
        on 
            co.id = edu.course_id
        join 
            users as u 
        on 
            per.id = u.id

        where 
            (volunteer_id = %(volunteer_id)s)
    """
    vars = {"volunteer_id": user.id}
    if college_name:
        sql += "and (edu.college_name = %(college_name)s);"
        vars.update({"college_name": college_name})
    
    elif email_id:
        sql += "and (u.email_id = %(email_id)s)"
        vars.update({"email_id": email_id})

    elif name:
        re_name = f"%{name}%"
        sql += "and (lower(per.full_name) like lower(%(name)s));"
        vars.update({"name": re_name})

    elif beneficiary_status == "new":
        sql += "and (per.is_verified = false);"
    
    elif beneficiary_status == "verified":
        sql+= "and (per.is_verified = true);"
    
    # print(sql)

    beneficiaries = execute_sql_select_statement(sql, vars)


    return templates.TemplateResponse("beneficiary_profile.html", {
        "request": request, "user": user, "beneficiaries": beneficiaries, 
        "email_id": email_id, "beneficiary_status": beneficiary_status,
        "name": name
    })