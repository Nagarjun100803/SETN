from typing import Literal
from fastapi import APIRouter, Body, Form, Request, Response, status, Depends
from database import execute_sql_select_statement, execute_sql_commands, execute_sql_commands_with_multiple_params
import schemas
from oauth2 import get_current_admin
from config import templates
import pandas as pd


router = APIRouter(
    tags = ['Admin'],
    prefix = "/admin"
)


@router.get("/all_applications")
def get_all_applications(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin)
):
    sql: str = """
        select 
            per.id as beneficiary_id,
            per.full_name as name,
            c.degree,
            c.department,
            c.course,
            edu.college_name,
            f.beneficiary_status,
            f.parental_status,
            f.total_annual_family_income,
            f.house_status,
            f.special_consideration,
            f.reason_for_expecting_financial_assistance, 
            f.special_consideration,
            f.have_failed_in_any_subject_in_last_2_sem,
            f.latest_sem_perc,
            f.previous_sem_perc,
            f.current_semester,
            f.difference_in_sem_perc
        from 
            financial_assistance_applications as f
        join 
            beneficiary_personal_details as per
        on 
            f.beneficiary_id = per.id
        join 
            beneficiary_educational_details as edu
        on 
            f.beneficiary_id = edu.id
        join 
            courses as c
        on
            edu.course_id = c.id
        ; 

        """
    applications = execute_sql_select_statement(sql)
    # print(applications)
    return templates.TemplateResponse("applications.html", {"request": request, "user": user, "applications": applications})


@router.get("/beneficiaries")
async def get_beneficiary_profile(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin),
    beneficiary_status: Literal["all", "new", "verified"] = "all",
    college_name: str | None = "",
    email_id: str | None = "",
    name: str = ""
):
    """
        Endpoint fetches basic details of all beneficiaries. 
    """
    sql: str = """
        select 
            per.id as id,
            per.full_name as name,
            co.course,
            co.degree,
            co.department,
            edu.college_name,
            per.date_of_birth,
            per.phone_num,
            --per.aadhar_num,
            u.email_id,
            per.is_verified
        from 
            beneficiary_personal_details as per
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
        
    """
    vars = None
    
    if email_id:
        sql += "where u.email_id = %(email_id)s;"
        vars = {"email_id": email_id}

    elif name:
        re_name: str = f"%{name}%"
        sql += "where lower(per.full_name) like lower(%(name)s)"
        vars = {"name": re_name}

    elif college_name:
        sql += "where edu.college_name = %(college_name)s"
        vars = {"college_name": college_name}
        
    elif beneficiary_status == "new":
        sql += "where per.is_verified = false;"
    
    elif beneficiary_status == "verified":
        sql+= "where per.is_verified = true;"

    
    beneficiaries = execute_sql_select_statement(sql, vars)

    return templates.TemplateResponse("beneficiary_profile.html", {
        "request": request, "user": user, "beneficiaries": beneficiaries, 
        "email_id": email_id, "beneficiary_status": beneficiary_status,
        "name": name
        })




@router.get("/application_periods")
def get_application_period_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin)
):
    return templates.TemplateResponse("application_period.html", {"request": request, "user": user})



@router.post("/application_periods")
def create_new_application_period(
    request: Request,
    application_period: schemas.ApplicationPeriod = Form(),
    user: schemas.TokenData = Depends(get_current_admin),
):
    sql: str = """
        insert into application_periods
            (academic_year, semester, start_date, end_date)
        values
            (%(academic_year)s, %(semester)s, %(start_date)s, %(end_date)s)
        ;
    """
    # Create new application period.
    execute_sql_commands(sql, application_period.model_dump())

    return templates.TemplateResponse("application_period.html", {"request": request, "user": user, "message": "Application period created."})



@router.get("/beneficiary/{beneficiary_id}")
def get_beneficiary_full_details(
    request: Request, 
    beneficiary_id: int,
    user: schemas.TokenData = Depends(get_current_admin)
):
    """This endpoint returns the full detail of a beneficiary."""
    pass



@router.get("/assign_beneficiaries")
def get_assign_beneficiaries_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin)
):
    """
        This endpoint only shows the new beneficiaries and allow admins to select beneficaries
        to assign to the particular volunteer. 
    """
    
    context: dict = {"request": request, "user": user}
    
    beneficiary_sql: str = """
        select 
            per.id as id,
            per.full_name as name,
            co.course,
            co.degree,
            co.department,
            edu.college_name,
            per.phone_num
            --per.date_of_birth,
            --per.aadhar_num,
            --u.email_id,
            --per.is_verified
        from 
            beneficiary_personal_details as per
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
            (per.is_verified = false) and 
            (not exists(
                select 
                    1 
                from 
                    beneficiary_assignments as ba
                where 
                    ba.beneficiary_id = u.id
            ))
        ;   
    """
    
    beneficiaries = execute_sql_select_statement(beneficiary_sql)
    if not beneficiaries:
        context.update({"message_type": "Info", "message": "All new beneficiaries are assigned / No new beneficiaries"})
        return templates.TemplateResponse("message.html", context)
    
    volunteers_sql: str = "select id, username from users where users.role = 'volunteer';"
    volunteers = execute_sql_select_statement(volunteers_sql)
    
    context.update({"beneficiaries": beneficiaries, "volunteers": volunteers})
    
    return templates.TemplateResponse("beneficiary_assign.html", context)



@router.post("/assign_beneficiaries")
def allocate_beneficiaries(
    request: Request,
    beneficiaries_id: list[int] = Form() ,
    volunteer_id: int = Form(),
    user: schemas.TokenData = Depends(get_current_admin)
):
    
    sql: str = """
        insert into beneficiary_assignments(
            beneficiary_id, volunteer_id, assigned_by
        )
        values
            %s
        ;
    """
    total_records = len(beneficiaries_id)
    vars: list[dict] = pd.DataFrame(
        {
            "beneficiary_id": beneficiaries_id, 
            "volunteer_id": [volunteer_id] * total_records,
            "assigner_id": [user.id] * total_records
        }
    ).to_dict("records")

    execute_sql_commands_with_multiple_params(
        sql, vars, template = "(%(beneficiary_id)s, %(volunteer_id)s, %(assigner_id)s)"
    )

    return templates.TemplateResponse("message.html", {
        "request": request, "user": user, "message_type": "Success",
        "message": "Beneficiaries assisgned successfully."
    })