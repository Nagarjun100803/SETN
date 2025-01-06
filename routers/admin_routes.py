from typing import Literal
from fastapi import APIRouter, Form, Request, Response, status, Depends
from database import execute_sql_select_statement, execute_sql_commands
import schemas
from oauth2 import get_current_admin
from config import templates


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



@router.get("/application/uploads")
def get_application_uploads(
    request: Request, 
    beneficiary_id: int, current_semester: int,
    document: Literal['latest_sem_marksheet', 'previous_sem_marksheet', 'bonafide_or_fee_paid_proof'], 
    admin: schemas.TokenData = Depends(get_current_admin)
):

    sql: str = """
        select 
            f.latest_sem_marksheet,
            f.previous_sem_marksheet,
            f.bonafide_or_fee_paid_proof,
            per.full_name
        from 
            financial_assistance_applications as f
        join 
            beneficiary_personal_details as per
        on 
            f.beneficiary_id = per.id
        where 
            beneficiary_id = %(beneficiary_id)s and current_semester = %(current_semester)s 
        ; 
    """
    vars: dict = {'beneficiary_id': beneficiary_id, "current_semester": current_semester}

    data = execute_sql_select_statement(sql, vars, fetch_all = False)

    if not data:
        return None

    upload: None | bytes = data[document]
    if not upload:
        return {"Message": "This applicant haven't uploaded this data."}
        
 
    filename = f'{data['full_name'].strip().lower().replace(' ', '_')}_{beneficiary_id}_sem_{current_semester}_{document}.pdf'
    
    return Response(
        upload, media_type = "application/pdf",
        headers = {
            "Content-Disposition": f"inline; filename = {filename}",
            "Cache-Control": "public, max-age=600" # 10 Mins
        }
    )



@router.get("/beneficiary_profile_pic/{beneficiary_id}")
async def get_beneficiary_profile_picture(
    request: Request,
    beneficiary_id: int 
):
    sql: str = """
        select
            full_name, 
            passport_size_pic 
        from 
            beneficiary_personal_details 
        where 
            id = %(id)s;
    """
    user_data = execute_sql_select_statement(sql, {"id": beneficiary_id}, fetch_all = False)
    
    if not user_data:
        return None 
    
    profile_pic = user_data['passport_size_pic']
    beneficiary_name: str = user_data['full_name'].strip().lower().replace(' ', '_')

    file_name = f'{beneficiary_name}_profile_pic'

    return Response(
        profile_pic, media_type = "image/jpeg", # Ensure MIME type
        headers= {
        "Content-Disposition": f"inline; filename={file_name}.jpeg",
        "Cache-Control": "public, max-age=6000",  # Cache for 10 minutes
    }) 


@router.get("/beneficiary_marksheets/{beneficiary_id}")
def get_marksheet(
    request: Request,
    beneficiary_id: int,
    marksheet: Literal['tenth_marksheet', 'twelveth_marksheet']
):
    
    """Endpoint used to get the marksheet uploaded by the beneficiary."""
    # Query the marksheet uploaded by the beneficiary.
    sql: str = """
        select 
            tenth_marksheet, 
            twelveth_marksheet
        from 
            beneficiary_educational_details
        where 
            id = %(beneficiary_id)s
        ;
    """

    vars = {"beneficiary_id": beneficiary_id}

    data = execute_sql_select_statement(sql, vars, fetch_all = False)
    

    marksheet_data: bytes | None = data[marksheet]
    
    if not marksheet_data:
        return None 
    
    return Response(
        marksheet_data, 
        media_type = "application/pdf", 
        headers = {
            "Content-Disposition": f"inline; filename=beneficiary_{beneficiary_id}_{marksheet}.pdf",
            "Cache-Control": "public, max-age=600"
        }
    )

@router.get("/beneficiaries")
async def get_beneficiary_profile(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin)
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
        order by 
            per.id
        ;
    """
    
    beneficiaries = execute_sql_select_statement(sql)

    return templates.TemplateResponse("beneficiary_profile.html", {"request": request, "user": user, "beneficiaries": beneficiaries})




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


@router.get("/beneficiary/verify/{beneficiary_id}")
def get_beneficiary_profile_verify_page(
    request: Request,
    beneficiary_id: int,
    user: schemas.TokenData = Depends(get_current_admin)
):
    """This endpoints returns the all the profile details of the benenficiary"""
    
    context: dict = {"request": request, "user": user}

    sql: str = """
        select 
            u.email_id, per.id, per.full_name, per.gender, per.phone_num, per.gheru_naav, per.date_of_birth,
            par.father_name, par.mother_name, par.father_occupation, par.mother_occupation,
            par.address_line, par.city, par.district, par.pincode,
            edu.tenth_perc, edu.twelveth_perc, edu.college_name, edu.college_type, edu.university,
            c.course, c.degree, c.department, per.is_verified
        from 
            beneficiary_personal_details as per
        join 
            beneficiary_parental_details as par
        on 
            per.id = par.id
        join 
            beneficiary_educational_details as edu
        on 
            per.id = edu.id 
        join 
            courses as c
        on 
            edu.course_id = c.id
        join 
            users as u 
        on 
            u.id = per.id
        where 
            per.id =  %(beneficiary_id)s
        ;
    """

    profile = execute_sql_select_statement(sql, {"beneficiary_id": beneficiary_id}, fetch_all = False)

    if not profile:
        context.update({"message": "No user found with this id."})
        return templates.TemplateResponse("message.html", context)

    context.update({"profile": profile})
    return templates.TemplateResponse("beneficiary_verify.html", context)



@router.post("/beneficiary/verify/{beneficiary_id}")
def make_profile_verified(
    request: Request,
    beneficiary_id: int,
    user: schemas.TokenData = Depends(get_current_admin),
    remarks_form: schemas.RemarksSchema = Form()
):
    """After the manual verifiaction the admin add a remarks about the student and submit the
    remarsk that will update to the beneficiary table. So that he can apply for scholarship."""

    sql: str = """
        update 
            beneficiary_personal_details
        set 
            remarks = %(remarks)s,
            is_verified = true
        where 
            id = %(beneficiary_id)s
        ;
    """
    vars = {"beneficiary_id": beneficiary_id, "remarks": remarks_form.remarks}
    profile = execute_sql_commands(sql, vars)

    return templates.TemplateResponse("message.html", {"request": request, "user": user, "message": "Beneficiary verified successfully."})




@router.get("/beneficiary/{beneficiary_id}")
def get_beneficiary_full_details(
    request: Request, 
    beneficiary_id: int,
    user: schemas.TokenData = Depends(get_current_admin)
):
    """This endpoint returns the full detail of a beneficiary."""
    pass
