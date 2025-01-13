from fastapi import APIRouter, Request, status, Depends, Response, Form
from database import execute_sql_select_statement
import schemas
from typing import Literal
from oauth2 import get_current_admin_or_volunteer
from config import templates
from database import execute_sql_commands
from database import db
from psycopg2.extensions import connection, cursor

router = APIRouter(
    tags = ["Admin & Volunteer"],
    prefix = "/admin_and_volunteer"  
)



async def check_edit_access(
    beneficiary_id: int, # Automatically injected by the FastAPI.
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer)
) -> bool:
    

    if user.role == "admin":
        return True
     
    sql: str = """
        select 
            1
        from 
            beneficiary_assignments
        where 
            beneficiary_id = %(beneficiary_id)s and volunteer_id = %(volunteer_id)s
        ;
    """

    edit_permission = execute_sql_select_statement(sql, {"beneficiary_id": beneficiary_id, "volunteer_id": user.id}, fetch_all = False)

    return bool(edit_permission) 


async def get_beneficiary_verification_status(beneficiary_id: int) -> bool:
    # Check whether the beneficary verified.
    
    sql: str = """
        select  
            verification_status
        from 
            beneficiary_assignments
        where 
            beneficiary_id = %(beneficiary_id)s
    """ 
    beneficiary_record = execute_sql_select_statement(
        sql, {"beneficiary_id": beneficiary_id}, fetch_all = False
    )

    if not beneficiary_record:
        return None
    return beneficiary_record["verification_status"]

@router.get("/beneficiary_profile_pic/{beneficiary_id}")
async def get_beneficiary_profile_picture(
    request: Request,
    beneficiary_id: int,
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer) 
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
    marksheet: Literal['tenth_marksheet', 'twelveth_marksheet'],
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer) 

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

@router.get("/application/uploads")
def get_application_uploads(
    request: Request, 
    beneficiary_id: int, current_semester: int,
    document: Literal['latest_sem_marksheet', 'previous_sem_marksheet', 'bonafide_or_fee_paid_proof'], 
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer) 

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



@router.get("/beneficiary/explore/{beneficiary_id}")
def get_beneficiary_profile_verify_page(
    request: Request,
    beneficiary_id: int,
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer),
    edit_permission: bool = Depends(check_edit_access) 
    # It calls the function with necessary params. Takes the beneficiary_id from this route to actual check_edit_access function. 
):
    """This endpoints returns the all the profile details of the benenficiary"""
    
    context: dict = {"request": request, "user": user}

    # Sql to fetch the details of the beneficiary.
    sql: str = """
        select 
            u.email_id, per.id, per.full_name, per.gender, per.phone_num, per.gheru_naav, per.date_of_birth, per.remarks,
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
        context.update({"message": "No user found with this id.", "message_type": "Error"})
        return templates.TemplateResponse("message.html", context)

    # Update the edit permission in the profile.    
    profile.update({"edit_permission": edit_permission})
    # print(profile)
    context.update({"profile": profile}) # Update the context with profile.
    return templates.TemplateResponse("beneficiary_verify.html", context)



@router.post("/beneficiary/explore/{beneficiary_id}")
def make_profile_verified(
    request: Request,
    beneficiary_id: int,
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer),
    verification_status: str = Depends(get_beneficiary_verification_status),
    edit_permission: bool = Depends(check_edit_access),
    remarks_form: schemas.RemarksSchema = Form()
):
    """
        After the manual verifiaction the admin add a remarks about the student and submit the
        remarsk that will update to the beneficiary table. So that he can apply for scholarship.
    """

    # If the user dont have access to update we return the error message.
    context = {"request": request, "user": user}
    
    if not edit_permission:
        context.update({"message": "You dont have access to perform this action.", "message_type": "Error"})
        return templates.TemplateResponse("message.html", context,)

    # Check whether this is the first time verification.
    if verification_status == "complete":
        # Only updating the remarks.
        sql: str = """
            update 
                beneficiary_personal_details
            set 
                remarks = %(remarks)s
            where 
                id = %(beneficiary_id)s
            ;
        """
        vars = {"remarks": remarks_form.remarks, "beneficiary_id": beneficiary_id}
        profile_update: None = execute_sql_commands(sql, vars)

        context.update({"message": "Beneficiary remarks updated successfully", "message_type": "Success"})
        return templates.TemplateResponse("message.html", context)
    
    
    # First time verification. So need to update both beneficiary_assignment table 
    # and personal details table.

    # Get a connection
    conn: connection = db.getconn()
    cur: cursor = conn.cursor()

    # Update the personal details table.
    try:
        sql: str = """
        update 
            beneficiary_personal_details
        set 
            remarks = %(remarks)s,
            is_verified = true,
            verified_by = %(verifier_id)s
        where 
            id = %(beneficiary_id)s
        ;
            """
        vars = {"beneficiary_id": beneficiary_id, "remarks": remarks_form.remarks, "verifier_id": user.id}
        profile = cur.execute(sql, vars)

        # Next update the beneficiary assignment.
        sql: str = """
            update 
                beneficiary_assignments
            set 
                verification_status = 'complete', verified_at = 'now()'
            where 
                beneficiary_id = %(beneficiary_id)s and volunteer_id = %(volunteer_id)s
            ;
        """
        vars = {"beneficiary_id": beneficiary_id, "volunteer_id": user.id}
        beneficiary_assignment_update: None = cur.execute(sql, vars)
        
        conn.commit()

    except Exception as e:
        print(f"Error occur during updating the record: {str(e)}")
        raise(e)
    
    finally:
        cur.close()
        db.putconn(conn)
    context.update({"message": "Beneficiary Verified Successfully.", "message_type": "Success"})
    return templates.TemplateResponse("message.html", context)

