from typing import Literal
from fastapi import APIRouter, Body, Form, HTTPException, Query, Request, Response, status, Depends
from database import execute_sql_select_statement, execute_sql_commands, execute_sql_commands_with_multiple_params
import schemas
from oauth2 import get_current_admin
from config import templates
import pandas as pd


router = APIRouter(
    tags = ['Admin'],
    prefix = "/admin"
)




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


@router.get("/new_sponsor")
def get_sponsor_create_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin)
):
    context: dict = {"request": request, "user": user}
    
    return templates.TemplateResponse("sponsor_create.html", context)


@router.post("/new_sponsor")
def create_new_sponsor(
    request: Request,
    sponsor: schemas.SponsorCreate = Form(),
    user: schemas.TokenData = Depends(get_current_admin),
):
    
    context: dict = {"request": request, "user": user}
    
    sql: str = """
        select
            exists(
                select
                    1
                from 
                    sponsors
                where 
                    email_id = %(email_id)s
            ) as email_exist,

            exists(
                select 
                    1
                from 
                    sponsors
                where 
                    phone_num = %(phone_num)s
            ) as phone_num_exist,

            exists(
                select 
                    1
                from 
                    sponsors
                where 
                    full_name = %(full_name)s
            ) as full_name_exist
    """
    vars: dict = sponsor.model_dump()

    previous_record_flag = execute_sql_select_statement(sql, vars, fetch_all = False)
    
    atleast_one_previous_record_flag = pd.Series(previous_record_flag).any() # return True if any one value is True

    if atleast_one_previous_record_flag:

        if previous_record_flag.get("email_exist"):
            context.update({"message": "Email Id already exist"})
        
        elif previous_record_flag.get("phone_num_exist"):
            context.update({"message": "Contact Number already exist"}) 
        
        elif previous_record_flag.get("full_name_exist"):
            context.update({"message": "Name already exist"})
        
        context.update({"sponsor": vars, "message_type": "Error"})
        
        return templates.TemplateResponse("sponsor_create.html",context)
    
    # Create a new sponsor.

    create_sponsor_sql: str = """
        insert into 
            sponsors(
                full_name, phone_num, email_id, location, country, average_contribution
            )
        values
            (%(full_name)s, %(phone_num)s, %(email_id)s, %(location)s, %(country)s, %(average_contribution)s)
        ;
    """

    new_sponsor: None = execute_sql_commands(create_sponsor_sql, vars)

    context.update({"message": "Sponsor Created.", "message_type": "Success"})
    return templates.TemplateResponse("sponsor_create.html", context)
            

@router.get("/add_scholarship_amount")
def get_add_scholarship_amount_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin),
    beneficiary_details: schemas.AddFundQuery = Query()
):
    context: dict = {"request": request, "user": user}

    # Get all sponsor data that used to add fund to students.
    sql: str = """
        select
            id,
            full_name
        from 
            sponsors
        ;
    """
    sponsors = execute_sql_select_statement(sql)

    context.update({"sponsors": sponsors, "beneficiary_details": beneficiary_details.model_dump()})
    # print(context)
    
    return templates.TemplateResponse("sample.html", context)

    
@router.post("/add_scholarship_amount")
def create_scholarship_record(
    request: Request,
    scholarship_data: schemas.CreateScholarship = Form(),
    user: schemas.TokenData = Depends(get_current_admin),
):
    
    context: dict = {"request": request, "user": user}
    # check for the previous fund transaction of same application to avoid redundancy.
    previous_fund_sql: str = """
            select 
                case
                    when (amount is not null) or (sponsor_id is not null) then true
                    else false
                end as previous_allocation
            from 
                approved_applications
            where 
                application_id = %(application_id)s 
            ;
    """
    vars = {"application_id": scholarship_data.application_id}

    previous_fund = execute_sql_select_statement(previous_fund_sql, vars, fetch_all = False)

    if not previous_fund:
        raise HTTPException(400, details = "Something went wrong.")        

    if previous_fund["previous_allocation"]:
        context.update({
            "message": "Fund already allocated to this application",
            "message_type": "Info"
        })
        return templates.TemplateResponse("message.html", context)
    

    # Create a new fund allocation record.
    create_fund_sql: str = """
            update
                approved_applications
            set 
                amount = %(amount)s, 
                sponsor_id = %(sponsor_id)s,
                transfered_at = now()
            where 
                application_id = %(application_id)s
            ;
    """
    vars = scholarship_data.model_dump()

    new_fund = execute_sql_commands(create_fund_sql, vars)

    context.update({
        "message": "Fund allocated",
        "message_type": "Info"
    })

    return templates.TemplateResponse("message.html", context)