from fastapi import APIRouter, HTTPException, Query, Request, status, Depends, Response, Form
from fastapi.responses import ORJSONResponse
from database import execute_sql_select_statement, execute_sql_commands, db
import schemas
from typing import Literal
from oauth2 import get_current_admin_or_volunteer
from config import templates
from psycopg2.extensions import connection, cursor
from psycopg2.extras import RealDictRow
import pandas as pd
from utils import custom_data_type_conversion


router = APIRouter(
    tags = ["Admin & Volunteer"],
    prefix = "/admin_and_volunteer"  
)

async def get_latest_application_period() -> int :

    sql: str = """
        select 
            id
        from 
            application_periods
        order by 
            opened_at desc
        limit 
            1
        ;
    """
    latest_application_period: RealDictRow = execute_sql_select_statement(
        sql, fetch_all = False
    )


    if not latest_application_period:
        raise HTTPException(404, detail = "No application period found")
    
    return latest_application_period.get("id")



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
    vars: dict = {"beneficiary_id": beneficiary_id, "current_semester": current_semester}

    data = execute_sql_select_statement(sql, vars, fetch_all = False)

    if not data:
        return None

    upload: None | bytes = data[document]
    if not upload:
        return {"Message": "This applicant haven't uploaded this data."}
        
 
    filename = f"""{data.get("full_name").strip().lower().replace(' ', '_')}_{beneficiary_id}_sem_{current_semester}_{document}.pdf"""
    
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


    vars: dict =  {
        "beneficiary_id": beneficiary_id, 
        "remarks": remarks_form.remarks,
        "verifier_id": user.id
    }

    conn = db.getconn()
    cur = conn.cursor()

    # Check the beneficiary handler(admin or volunteer), if beneficiary id found in beneficiary assignment table,
    # The benficiary assigned to volunteer, else the benenficiary is handling by admin.
    verification_check_sql: str = """
        select 
            per.id,
            per.remarks as old_remarks,
            per.is_verified,
            per.verified_by,
            ba.volunteer_id as is_assigned, -- Here volunteer id used as flag to know whether the beneficiary is handled by admin or hand over to volunteer.
            ba.assigned_by,
            ba.verification_status
        from 
            beneficiary_personal_details as per
        left join 
            beneficiary_assignments as ba
        on 
            per.id = ba.beneficiary_id
        where 
            per.id = %(beneficiary_id)s
    """
    
    # beneficiary_record = execute_sql_select_statement(sql, vars, fetch_all = False)
    cur.execute(verification_check_sql, vars)
    beneficiary_record = cur.fetchone()

    if not beneficiary_record:
        context.update({"message": "Something Went Wrong!", "message_type": "Error"})
        return templates.TemplateResponse("message.html", context)
    
    # Conditions to update remarks.
    # 1, if beneficiary assigned to volunteer and verifiation status = 'complete'
    # 2, if beneficiary handled by admin and the is_verified = true in beneficiary_personal_details table.

    if ((beneficiary_record["is_assigned"] and beneficiary_record["verification_status"] == "complete") or (beneficiary_record["is_verified"])):

        remarks_update_sql: str = """
                update 
                    beneficiary_personal_details
                set 
                    remarks = %(remarks)s
                where 
                    id = %(beneficiary_id)s
        """
        remarks_update: None = cur.execute(remarks_update_sql, vars)
        cur.close()
        db.putconn(conn)
        context.update({"message": "Beneficiary remarks updated successfully", "message_type": "Success"})
        return templates.TemplateResponse("message.html", context)
    

    # Create verification data(Fresh verification) and also update that in beneficiary assignment.
    # Get a connection

    # Update the personal details table.
    try:
        print("Enter into verification condition")
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
        profile = cur.execute(sql, vars)

        # Next update the beneficiary assignment.
        sql: str = """
            update 
                beneficiary_assignments
            set 
                verification_status = 'complete', verified_at = now()
            where 
                beneficiary_id = %(beneficiary_id)s
            ;
        """
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


@router.get("/application_filters")
def get_application_filters(
    request: Request,
    application_period_id: int,
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer)
):
    sql: str = """
        select 
            edu.college_name,
            f.beneficiary_status,
            par.district,
            f.current_semester,
            concat(c.degree, ' ', c.department) as course_and_department
        from 
            financial_assistance_applications as f
        join 
            beneficiary_educational_details as edu
        on 
            f.beneficiary_id = edu.id
        join 
            courses as c
        on
            edu.course_id = c.id
        join 
            beneficiary_parental_details as par 
        on 
            par.id = f.beneficiary_id
        left join 
            beneficiary_assignments as ba
        on 
            ba.beneficiary_id = f.beneficiary_id
        where 
            (f.application_period_id = %(application_period_id)s)
    """
    
    vars = {"application_period_id": application_period_id}

    if user.role == 'volunteer':
        # Add a where clause so that they can only see the particular results.
        sql += " and (ba.volunteer_id = %(user_id)s)"
        vars.update({"user_id": user.id})

    result = execute_sql_select_statement(sql, vars)

    # Converting into dataframe object to get unique values.
    filter_values_df = pd.DataFrame(result)

    if filter_values_df.empty:
        return None

    filters: dict = {}
    filter_values_df["current_semester"] = filter_values_df["current_semester"].apply(custom_data_type_conversion)
    
    # Iterate each column and get unique values.
    for col in filter_values_df.columns:
        filters.update({col: list(filter_values_df[col].sort_values().unique())})

    # print(filters)
    return ORJSONResponse(
        filters, headers = {
            # "Cache-Control": "public, max-age=1800" # 15 minutes cache.
        }
    )


@router.get("/get_application_periods")
def get_applications_select_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer),    
):
    
    application_period_overview_sql: str = """
        select 
            x.*,
            ap.academic_year,
            upper(ap.semester) as semester
        from(
            select 
                f.application_period_id,
                sum(aap.amount)::int as total_amount_distribution,
                count(f.id) as total_applications
            from 
                financial_assistance_applications as f
            left join 
                approved_applications as aap
            on 
                aap.application_id = f.id
            group by 
                f.application_period_id
        )x 
        join 
            application_periods as ap 
        on 
            x.application_period_id = ap.id
        order by 
                x.application_period_id desc
        ;
    """

    application_period_overiview = execute_sql_select_statement(application_period_overview_sql)

    context: dict = {"user": user, "request": request, "application_periods": application_period_overiview}
    
    return templates.TemplateResponse("applications_overview.html", context)


@router.get("/applications")
def get_all_applications(
    request: Request,
    # application_period_id: int ,
    filter_params: schemas.ApplicationFilterParams = Query(),
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer),
):
    """
        Endpoint provides the applications applied by the beneficiaries.
        Admin can see all the applications.
        Volunteer can only see the application assoscaited by their beneficiaires
    """
    
    sql: str = """
        select 
            per.id as beneficiary_id,
            f.application_period_id,
            per.full_name as name,
            u.email_id,
            c.degree,
            c.department,
            c.course,
            edu.college_name,
            f.beneficiary_status,
            par.district,
            f.current_semester,
            f.is_verified as status
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
        join 
            beneficiary_parental_details as par 
        on 
            par.id = f.beneficiary_id
        join 
            users as u 
        on 
            u.id = f.beneficiary_id
        left join 
            beneficiary_assignments as ba
        on 
            ba.beneficiary_id = f.beneficiary_id
        where 
            (f.application_period_id = %(application_period_id)s)
        """   
    vars: dict = {"application_period_id": filter_params.application_period_id} # Used to store the db parameters
    if user.role == "volunteer":
        # Add a where clause so that they can only see the particular results.
        sql += " and (ba.volunteer_id = %(user_id)s)"
        vars.update({"user_id": user.id})
    

    # Applying Filters
    if filter_params.name:
        re_name: str = f"%{filter_params.name}%"
        sql += " and (lower(per.full_name) like lower(%(name)s))"
        vars.update({"name": re_name}) 
    
    elif filter_params.email_id:
        sql += " and (u.email_id = %(email_id)s)"
        vars.update({"email_id": filter_params.email_id})
    
    else: 
        filter_mapper: dict = {
            "semester": " and (f.current_semester = %(semester)s::int)",
            "location": " and (par.district = %(location)s)",
            "college_name": " and (edu.college_name = %(college_name)s)",
            "beneficiary_status": " and (f.beneficiary_status = %(beneficiary_status)s)", 
            "application_status": " and (f.is_verified = %(application_status)s)"
        }
        for filter_option, filter_option_value in filter_params.model_dump(exclude={"name", "email_id", "course", "application_handler", "application_period_id", "limit_size", "offset_size"}).items():
            if (filter_option_value is not None) and (filter_option_value != "") and (filter_option_value != 0):
                sql += filter_mapper[filter_option]
                vars.update({filter_option: filter_option_value})
        
        # Slice the course and department from the course.  
        if filter_params.course:
            sql += " and (c.degree = %(degree)s and c.department = %(department)s)"
            degree = filter_params.course[:2]
            department = filter_params.course[3:]
            vars.update({"degree": degree, "department": department})
    
    # Order the application in beneficiary_id 
    sql += """ 
        order by 
            f.is_verified
        ;      
    """
    vars.update({"limit": filter_params.limit_size, "offset": filter_params.offset_size})
    
    # print(sql)
    # print()
    # print(vars)

    applications = execute_sql_select_statement(sql, vars)

    context: dict = {"request": request, "user": user}

    if not applications:
        context.update({"message_type": "Error", "message": "Sorry No records to show."})
        return templates.TemplateResponse("message.html", context)
    
    context.update({"applications": applications, "filter_params": filter_params.model_dump()})
    
    return templates.TemplateResponse("applications.html", context)



@router.get("/application/explore/{beneficiary_id}")
def get_application(
    request: Request,
    beneficiary_id: int,
    application_period_id: int,
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer),
):
    
    context: dict = {"request": request, "user": user}

    sql: str = """
        with cte1 as( 
            select 
                *
            from( 
                select 
                    beneficiary_id, 
                    application_period_id as current_application_period_id, 
                    lag(application_period_id) over(
                            partition by beneficiary_id 
                            order by application_period_id
                    ) as previous_application_period_id 
                from 
                    financial_assistance_applications
                where 		
                    beneficiary_id = %(beneficiary_id)s
            )x
            where
                x.current_application_period_id = %(application_period_id)s
        )

        select 
            y.*, u.username as verifier_name, 
            ap.amount,
            s.full_name as sponsor_name,
            s.phone_num as sponsor_num,
            s.location as sponsor_location,
            s.country as sponsor_country,
            ap.transfered_at::date as transaction_date
      
        from(
            select 
                f.id, f.beneficiary_id, per.full_name, c.degree, c.course, c.department, edu.college_name,  
                f.application_period_id, f.beneficiary_status, f.parental_status, 
                f.total_annual_family_income, f.house_status, f.reason_for_expecting_financial_assistance, 
                f.special_consideration, f.have_failed_in_any_subject_in_last_2_sem, f.latest_sem_perc, f.previous_sem_perc,
                f.difference_in_sem_perc, f.current_semester, per.remarks, ap.academic_year, ap.semester, f.applied_at, f.is_verified as application_status,
                f.verified_by, f.verified_at, f.reason_for_rejection
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
                c.id = edu.course_id
            join 
                application_periods as ap
            on 
                ap.id = f.application_period_id
            where
                f.application_period_id in (
                    (select cte1.current_application_period_id from cte1), 
                    (select cte1.previous_application_period_id from cte1)
                ) and
                f.beneficiary_id = %(beneficiary_id)s
        )y 
        left join 
            users as u 
        on 
            u.id = y.verified_by
        left join 
            approved_applications as ap
        on 
            ap.application_id = y.id
        left join 
            sponsors as s
        on 
            s.id = ap.sponsor_id
        order by 
            y.application_period_id desc 
        ;
        
    """

    vars: dict = {"beneficiary_id": beneficiary_id, "application_period_id": application_period_id}

    applications = execute_sql_select_statement(sql, vars)
    
    # Check for no applications with this ID
    if not applications:
        context.update({"message": "Sorry! No records to show", "message_type": "Info"})
        return templates.TemplateResponse("message.html", context)

    applications_df = pd.DataFrame(applications)
    # applications_df.fillna(value = '', inplace = True) # If application_df contains any 'nan' values convert it into None for json serialization.
    
    general_details_columns: list[str] = ["beneficiary_id", "full_name", "degree", "course", "department", "college_name", "remarks"]
    general_details: dict = applications_df[general_details_columns].iloc[0].to_dict()

    # Select a column that are not in General details list.
    application_details: pd.DataFrame = applications_df[[col for col in applications_df.columns if col not in general_details]]
    
    # print(general_details)
    data = {"general_details": general_details}

    
    data.update({"current_application_details": application_details.iloc[0].to_dict()})
    # Update previous sem details if exists else update as None
    data.update({"previous_application_details": application_details.iloc[1].to_dict()}) if len(applications) > 1 else data.update({"previous_sem_details": None})
    
    # print(data)
    # return data
    context.update({"data": data})
    return templates.TemplateResponse("application_verification.html", context)


@router.post("/application/explore/{beneficiary_id}")
async def approve_or_reject_application(
    request: Request,
    beneficiary_id: int,
    user: schemas.TokenData = Depends(get_current_admin_or_volunteer),
    application_verification_schema: schemas.ApplicationVerification = Form()
):
    
    context: dict = {"request": request, "user": user}
    # Check if both are False.
    if not any([application_verification_schema.remarks, application_verification_schema.reason_for_rejection]):
        context.update({
            "message": "Require remarks or reason for rejection to proceed further.",
            "message_type": "Error"
        })
    
    try:

        # Get a database connection.
        conn: connection = db.getconn()
        cur: cursor = conn.cursor()

        # Check whether the application is already verified.
        application_verification_sql: str = """
            select 
                is_verified::boolean 
            from 
                financial_assistance_applications as f
            where 
                f.id = %(application_id)s
            ;
        """ 
        cur.execute(application_verification_sql, vars = {"application_id": application_verification_schema.application_id})
        verification_status = cur.fetchone()
        # print(f"The application verification status is {verification_status}")

        if verification_status["is_verified"]:
            context.update({
                "message": "Application Already Processed/Verified.",
                "message_type": "Info"
            })
            return templates.TemplateResponse("message.html", context)
        
        # Create a application verification record.
        create_application_verification_sql: str = """
            update 
                financial_assistance_applications
            set 
                is_verified = true,
                verified_by = %(verifier_id)s,
                verified_at = now(),
                remarks = %(remarks)s,
                reason_for_rejection = %(reason_for_rejection)s,
                conclusion = %(conclusion)s
            where 
                id = %(application_id)s
            ;
        """
        vars: dict = application_verification_schema.model_dump()
        vars.update({"verifier_id": user.id})
        cur.execute(create_application_verification_sql, vars)


        if application_verification_schema.conclusion == "accept":

            # check for application approval accidentaly before.
            application_approval_check_sql: str = """
                select 
                    1
                from 
                    approved_applications
                where 
                    application_id = %(application_id)s
                ;
            """
            vars = {"application_id": application_verification_schema.application_id}
            cur.execute(application_approval_check_sql, vars)
            application_approval_status = cur.fetchone()

            print(f"Tha application approval status is {application_approval_status}")
            if application_approval_status:
                context.update({
                    "message": "Application already approved.",
                    "message_type": "Info"
                })
                return templates.TemplateResponse("message.html", context)
        
            # Create application approval.
            application_approval_sql: str = """
                insert into approved_applications(application_id)
                    values(%(application_id)s);
            """
            cur.execute(application_approval_sql, vars)
        conn.commit()
            
    except Exception as e:
        conn.rollback()
        print(f"Error occur during application verification: {str(e)}")
        raise e
    
    finally:
        cur.close()
        db.putconn(conn)

    message_dict: dict = {"accept": "Application approved succesfully", "reject": "Application rejected succesfully"}

    context.update({"message": message_dict[application_verification_schema.conclusion], "message_type": "Info"})

    return templates.TemplateResponse("message.html", context)


# @router.get("/application/explore/{beneficiary_id}")
# def get_application(
#     request: Request,
#     beneficiary_id: int,
#     application_period_id: int,
#     user: schemas.TokenData = Depends(get_current_admin_or_volunteer),
# ):
    
#     # Need to write the logic to detect unexisting beneficiary id 
#     # and application_period id.
    
#     sql: str = """
#         select 
#             f.id, f.beneficiary_id, per.full_name, per.phone_num,  
#             c.degree, c.course, c.department, edu.college_name,  
#             f.application_period_id, f.beneficiary_status, f.parental_status, 
#             f.total_annual_family_income, f.house_status, f.reason_for_expecting_financial_assistance, 
#             f.special_consideration, f.have_failed_in_any_subject_in_last_2_sem, f.latest_sem_perc, f.previous_sem_perc,
#             f.difference_in_sem_perc, f.current_semester, per.remarks, ap.academic_year, ap.semester, f.applied_at, f.is_verified,
#             f.verified_by, v.full_name as verifier_name, f.verified_at, f.reason_for_rejection, f.conclusion,
#             s.full_name as current_sponsor_name, s.location as sponsor_location,
#             s.country as sponsor_country, s.phone_num as sponsor_phone_num,
#             aap.amount as contribution,
#             lag(s.full_name) over(partition by f.beneficiary_id order by f.application_period_id) as previous_sponsor_name,
#             lag(aap.amount) over(partition by f.beneficiary_id order by f.application_period_id) as previous_contribution,
#             aap.transfered_at
            
#         from 
#             financial_assistance_applications as f
#         join 
#             beneficiary_personal_details as per
#         on 
#             f.beneficiary_id = per.id 
#         join 
#             beneficiary_educational_details as edu
#         on 
#             f.beneficiary_id = edu.id
#         join 
#             courses as c 
#         on 
#             c.id = edu.course_id
#         join 
#             application_periods as ap
#         on 
#             ap.id = f.application_period_id
#         left join 
#             approved_applications as aap
#         on 
#             aap.application_id = f.id
#         left join 
#             sponsors as s
#         on 
#             s.id = aap.sponsor_id
#         left join 
#             admin_volunteers as v
#         on 
#             v.id = f.verified_by
#         where 
#             f.beneficiary_id = %(beneficiary_id)s and 
#             f.application_period_id <= %(application_period_id)s
#         order by 
#             f.application_period_id
#     """

#     # Fetching all application before this current application_period.
#     vars: dict = {"beneficiary_id": beneficiary_id, "application_period_id": application_period_id}
#     application_data = execute_sql_select_statement(sql, vars)

#     if not application_data:
#         return "No records to display."

#     applications_df = pd.DataFrame(application_data)

#     # Change the str into list[str] for special consideration column
#     applications_df["special_consideration"] = applications_df["special_consideration"].str.strip().str.split(".")
    
#     general_details_columns: list[str] = ["beneficiary_id", "full_name", "degree", "course", "department", "college_name", "phone_num"]
    
#     full_details: dict = dict()

#     general_details: dict = applications_df[general_details_columns].iloc[0].to_dict()

    
#     # Grab two applications that is current and previous applications[one step back]
#     required_columns: list[str] = [col for col in applications_df.columns if col not in general_details]
#     application_details = applications_df[required_columns].tail(2).to_dict("records")


#     # Select all previous applications and the remarks, conclusion and verifier name
#     history_columns: list[str] = ["id", "application_period_id", "academic_year", "semester", "remarks", "conclusion", "reason_for_rejection", "verifier_name", "contribution", "current_sponsor_name", "sponsor_phone_num"]
#     history_of_applications = applications_df[history_columns].iloc[::-1].to_dict("records")[1:]

#     full_details.update({
#         "general_details": general_details,
#         "history_of_applications": history_of_applications,
#         "application_details": application_details
#     })

#     # return full_details
#     return templates.TemplateResponse("application_view.html", {"request": request, "data": full_details})
    