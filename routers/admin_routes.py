from fastapi import APIRouter, Request, Response, status, Depends
from database import execute_sql_select_statement
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
            edu.id = c.id
        order by 
            f.difference_in_sem_perc desc, beneficiary_status
        ; 

        """
    applications = execute_sql_select_statement(sql)

    return applications




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
        "Cache-Control": "public, max-age=600",  # Cache for 10 minutes
    }) 



@router.get("/beneficiaries")
async def get_beneficiary_profile(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin)
):
    sql: str = """
        select 
            per.id as id,
            per.full_name as name,
            co.course,
            co.degree,
            co.department,
            edu.college_name 
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
        ;
    """
    
    beneficiaries = execute_sql_select_statement(sql)

    return templates.TemplateResponse("beneficiary_profile.html", {"request": request, "user": user, "beneficiaries": beneficiaries})



