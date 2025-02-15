from fastapi import APIRouter, Request, Response, Form, status, Depends, HTTPException
from config import templates
import schemas, utils
from database import execute_sql_select_statement, execute_sql_commands
from fastapi.responses import RedirectResponse
from oauth2 import get_current_beneficiary
import pandas as pd



router = APIRouter(
    prefix = "/beneficiary",
    tags = ["Beneficiary"]
)



course_sql: str = "select * from courses;"
courses = execute_sql_select_statement(course_sql)
course_df = pd.DataFrame(courses)



def get_course_list():

    final_data: dict = {} 
    # Grab all unique degree in that course. 
    for course in course_df['course'].unique():
        # Grab unique departments in each course and degree
        final_data[course] = {}
        for degree in course_df[course_df['course'] == course]['degree'].sort_values().unique().tolist():
            departments = course_df[(course_df['course'] == course) & (course_df['degree'] == degree)]['department'].sort_values().unique().tolist()
            final_data[course].update({degree: departments})    

    return final_data


def require_complete_profile(beneficiary: schemas.TokenData = Depends(get_current_beneficiary)) :
    """
        Ensures that the beneficiary's profile is complete before accessing the application endpoint.
        Redirects to the respective profile section if details are missing.
    """
    sql: str = """
        select 
            (select 1 from beneficiary_personal_details where id = %(beneficiary_id)s) as personal_detail,
            (select 1 from beneficiary_parental_details where id = %(beneficiary_id)s) as parental_detail,
            (select 1 from beneficiary_educational_details where id = %(beneficiary_id)s) as educational_detail
            --(select 1 from beneficiary_bank_details where id = %(beneficiary_id)s) as bank_detail
        ;
    """


    vars = {"beneficiary_id": beneficiary.id}
    profile = execute_sql_select_statement(sql, vars, fetch_all = False)

    if not profile['personal_detail']:
        raise HTTPException(status_code = 307, headers = {"Location": "/beneficiary/personal_details"})
    if not profile['parental_detail']:
        raise HTTPException(status_code = 307, headers = {"Location": "/beneficiary/parental_details"})
    if not profile['educational_detail']:
        raise HTTPException(status_code = 307, headers = {"Location": "/beneficiary/educational_details"})
    # if not profile['bank_detail']:
    #     raise HTTPException(status_code = 307, headers = {"Location": "/bank_details"})


def get_profile_status(beneficiary: schemas.TokenData = Depends(get_current_beneficiary)) -> bool:
    sql: str = """select is_verified from beneficiary_personal_details where id = %(beneficiary_id)s;"""
    profile = execute_sql_select_statement(sql, {'beneficiary_id': beneficiary.id}, fetch_all = False)

    if (not profile) or (not profile["is_verified"]):
        return False
    return True
     




@router.get("/personal_details")
def get_personal_details_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary)
):
    context: dict = {"request": request, "user": user}
    # Check the user already applied the details.
    personal_details_sql: str = "select 1 from beneficiary_personal_details where id = %(id)s;"
    previous_record = execute_sql_select_statement(personal_details_sql, {"id": user.id}, fetch_all = False)

    if previous_record:
        context.update({"message": "Already provided your personal details.", "message_type": "Info"})
        return templates.TemplateResponse("message.html", context)

    return templates.TemplateResponse("personal_details.html", context)



@router.get("/parental_details")
def get_parental_details_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary)
):
    context: dict = {"request": request, "user": user}
    #check the user already submited their details.
    parent_details_check_sql: str = """select 1 from beneficiary_parental_details where id = %(id)s;"""
    parent_details = execute_sql_select_statement(parent_details_check_sql, {'id': user.id}, fetch_all = False)

    if parent_details:
        context.update({"message": "Already provided your parental details", "message_type": "Info"})
        return templates.TemplateResponse("message.html", context)

    return templates.TemplateResponse("parental_details.html", context)




@router.get("/educational_details")
def get_educational_details_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary)
):
    context = {"request": request, "user": user}
    
    sql: str = "select 1 from beneficiary_educational_details where id = %(user_id)s;"
    previous_record = execute_sql_select_statement(sql, {'user_id': user.id}, fetch_all = False)

    if previous_record:
        context.update({"message": "Already provided your educational details"})
        return templates.TemplateResponse("message.html", context)

    course_list = get_course_list()
    context.update({"course": course_list})
    # print(context)
    return templates.TemplateResponse("educational_details.html", context)


# @router.get("/bank_details")
# def get_bank_details_page(
#     request: Request,
#     user: schemas.TokenData = Depends(get_current_beneficiary)
# ):
#     sql: str = """select 1 from beneficiary_bank_details where id = %(beneficiary_id)s;"""
    
#     previous_record = execute_sql_select_statement(sql, {"beneficiary_id": user.id})

#     if previous_record:
#         return templates.TemplateResponse("message.html", {"request": request, "user": user, "message_type": "Error", "message": "Already Filled Bank Details."})

#     return templates.TemplateResponse("bank_details.html", {"request": request, "user": user})



def get_application_period_data(beneficiary_id: int):
    
    application_period_sql: str = """
        select 
            *,
            case
                when end_date > now() then true  
        -- return true if the current date is less than end_date else false
                else false
            end as status,
        exists(  
        -- using exists to check whether the user already applied for the application_period
        -- return true if found a match else false.
                select 
                    id
                from 
                    financial_assistance_applications as fa
                where 
                    fa.application_period_id = application_periods.id and
                    fa.beneficiary_id = %(beneficiary_id)s
                
            ) as previous_application
        from 
            application_periods
        order by 
            opened_at desc
        limit 1
        ;

    """
    application_period_data = execute_sql_select_statement(
        application_period_sql, 
        {"beneficiary_id": beneficiary_id}, 
        fetch_all = False
    ) 

    # This is the formar of data {'id': 4, 'academic_year': '2024-2025', 'semester': 'even', 'start_date': datetime.date(2024, 12, 30), 'end_date': datetime.date(2025, 1, 30), 'opened_at': datetime.datetime(2024, 12, 31, 11, 50, 21, 763865), 'status': True, 'previous_application': True}
    # print(application_period_data)
    return application_period_data
    

@router.get("/financial_assistance_application")
def get_financial_assistance_application_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    profile = Depends(require_complete_profile),
    profile_status: bool = Depends(get_profile_status)
):
    application_period_data = get_application_period_data(user.id)
    context: dict = {"request": request, "user": user, "message_type": "Info", "application_period": application_period_data}

    if not profile_status:
        context.update({"message": "Your profile is not verified yet. Please wait for approval by the admin or contact them for assistance."})
        return templates.TemplateResponse("message.html", context)
    
    return templates.TemplateResponse("application_form.html", context)
        
    



@router.post("/personal_details") 
async def create_personal_details(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    personal_details: schemas.BeneficiaryPersonalInfo = Form()    
):
    
    context: dict = {"request": request, "user": user}

    previous_record_check_sql: str = """
        select 
            (select 
                1
            from 
                beneficiary_personal_details
            where
                id = %(id)s
            ) as personal_data_exist,

            (select 
                1
            from 
                beneficiary_personal_details
            where 
                aadhar_num = %(aadhar_num)s
            ) as aadhar_exists

    """
    vars = {"aadhar_num": personal_details.aadhar_num, "id": user.id}
    previous_record = execute_sql_select_statement(previous_record_check_sql, vars, fetch_all = False)

    print(previous_record)

    # If aadhar number already exist in table return error message in the same personal detail form.
    if previous_record["aadhar_exists"]:
        context.update({"personal_details": personal_details.model_dump()})
        context.update({"error_message": "Aadhar already exist."})
        print(context)
        return templates.TemplateResponse("personal_details.html", context)
    
    # If the user already entered personal data return the error message.
    if previous_record["personal_data_exist"]:
        context.update({"message": "You already provided your personal details."})
        return templates.TemplateResponse("message.html", context)


    full_name: str = personal_details.name.strip().replace(' ', '').title() + " " + personal_details.initial.strip().replace(' ', '').upper()

    data = personal_details.model_dump(exclude = {"initial", "name", "passport_size_pic"})
    processed_data = utils.get_processed_data(data)

    # read the file.
    file_content: bytes = await personal_details.passport_size_pic.read()

    # Compressed_file 
    compressed_file_content: bytes = utils.get_compressed_image(file_content)

    processed_data.update({"id": user.id, "full_name": full_name, "passport_size_pic": compressed_file_content})

    sql: str = """
                insert into beneficiary_personal_details(
                    id, full_name, name_as_in_passbook, gender, 
                    gheru_naav, aadhar_num, date_of_birth, phone_num, 
                    passport_size_pic
                )
                values(
                    %(id)s, %(full_name)s, %(name_as_in_passbook)s, %(gender)s, 
                    %(gheru_naav)s, %(aadhar_num)s, %(date_of_birth)s, %(phone_num)s, 
                    %(passport_size_pic)s
                )
                ;     
            """
    new_personal_details: None = execute_sql_commands(sql, processed_data) 


    return RedirectResponse('/beneficiary/parental_details', status.HTTP_302_FOUND)  

    
@router.post("/parental_details")
async def create_parental_details(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    parental_details: schemas.BeneficiaryParentalInfo = Form()
):

    # Check for the existance of previous record.
    previous_record_check_sql: str = "select 1 from beneficiary_parental_details where id = %(id)s;"
    previous_record = execute_sql_select_statement(previous_record_check_sql, {"id": user.id}, fetch_all = False)

    if previous_record:
        return templates.TemplateResponse(
            "message.html", {
                "request": request,
                "user": user,
                "message": "Already provided your parental details", 
                "message_type": "Info"
            }
        )
        
    parent_details = parental_details.model_dump(exclude = {"family_pic", "mother_name", "father_name"})
    
    # Standardize the data.
    processed_data: dict = utils.get_processed_data(parent_details)
    # Read the family_pic
    family_pic_content = await parental_details.family_pic.read() if parental_details.family_pic.size != 0 else None
    print(family_pic_content)

    processed_data.update({
        "id": user.id, "family_pic": family_pic_content, 
        "father_name": parental_details.father_name.upper(),
        "mother_name": parental_details.mother_name.upper()
    })

    sql: str = """
            insert into 
                beneficiary_parental_details
            values(
                %(id)s, %(father_name)s, %(mother_name)s, %(father_occupation)s, %(mother_occupation)s,
                %(parent_phone_num)s, %(address_line)s, %(city)s, %(district)s, %(pincode)s, %(family_pic)s
            )
            ;
    """
    new_parent_details: None = execute_sql_commands(sql, processed_data)

    return RedirectResponse("/beneficiary/educational_details", status.HTTP_302_FOUND)


    
    
@router.post("/educational_details")
async def create_educational_details(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    educational_details: schemas.BeneficiaryEducationalInfo = Form()
):
    
    previous_record_check_sql: str = """select 1 from beneficiary_educational_details where id = %(id)s"""
    previous_record = execute_sql_select_statement(previous_record_check_sql, {"id": user.id}, fetch_all = False)
    
    if previous_record:
        return templates.TemplateResponse(
            "message.html", {
                "request": request,
                "user": user,
                "message": "Already provided your educational details",
                "message_type": "Info"
            }
        )

    data = educational_details.model_dump(exclude = {"tenth_marksheet", "eleventh_marksheet", "twelveth_marksheet", "degree", "college_name"})
    data = utils.get_processed_data(data)

    course_id = course_df[
        (course_df['course'] == educational_details.course) & 
        (course_df['degree'] == educational_details.degree) &
        (course_df['department'] == educational_details.department)]['id'].values.tolist()[0]
  

    tenth_marksheet_content: bytes = await educational_details.tenth_marksheet.read() 
    eleventh_marksheet_content: bytes = await educational_details.eleventh_marksheet.read()
    twelveth_marksheet_content: bytes = await educational_details.twelveth_marksheet.read()



    data.update({
        "course_id": course_id, 
        "tenth_marksheet": tenth_marksheet_content,
        "eleventh_marksheet": eleventh_marksheet_content,
        "twelveth_marksheet": twelveth_marksheet_content,
        "college_name": educational_details.college_name.upper(),
        "id": user.id
    })
    
    sql: str = """
        insert into 
            beneficiary_educational_details(
                id, tenth_perc, eleventh_perc, twelveth_perc, course_id, college_name, 
                college_type, university, college_address, tenth_marksheet, 
                eleventh_marksheet, twelveth_marksheet 
        ) 
        values(
                %(id)s, %(tenth_perc)s, %(eleventh_perc)s, %(twelveth_perc)s, %(course_id)s, %(college_name)s, 
                %(college_type)s, %(university)s, %(college_address)s, %(tenth_marksheet)s, 
                %(eleventh_marksheet)s, %(twelveth_marksheet)s
       )
    """

    new_data: None = execute_sql_commands(sql, data)

    context: dict = {
        "message": "Your profile setup done.", 
        "message_type": "Profile Complete",
        "request": request, 
        "user": user
    } 
    return templates.TemplateResponse("message.html", context)



@router.post("/financial_assistance_application")
async def create_financial_assistance_form(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    application_form: schemas.FinancialAssistanceApplication = Form()
):
    application_period_data = get_application_period_data(user.id)
    context: dict = {"request": request, "user": user}
    # Computed again to avoid duplicate submission of data from malicious user or accident submission by refresh.
    if application_period_data["previous_application"]:
        return templates.TemplateResponse("application_form.html", {"request": request, "user": user, "application_period": application_period_data})

    data = application_form.model_dump(exclude = {'latest_sem_marksheet', 'previous_sem_marksheet', 'bonafide_or_fee_paid_proof', 'special_consideration'})

    # Calculate the difference in Semester percentage.
    difference_in_sem_perc: float = round(application_form.latest_sem_perc - application_form.previous_sem_perc, 2)

    # Make the special consideration as single text.
    special_considerations: str = ", ".join(application_form.special_consideration)    
    # Reading all the data.
    latest_sem_marksheet_content = await application_form.latest_sem_marksheet.read()
    previous_sem_marksheet_content = await application_form.previous_sem_marksheet.read()

    bonafide_fee_paid_proof_content = await application_form.bonafide_or_fee_paid_proof.read() \
                                        if application_form.bonafide_or_fee_paid_proof.size != 0 else None

    # All values
    data.update({
        "beneficiary_id": user.id,
        "special_consideration": special_considerations,
        "latest_sem_marksheet": latest_sem_marksheet_content,
        "previous_sem_marksheet": previous_sem_marksheet_content,
        "bonafide_or_fee_paid_proof": bonafide_fee_paid_proof_content,
        "difference_in_sem_perc": difference_in_sem_perc

    })
    sql: str = """
        insert into 
            financial_assistance_applications(
            beneficiary_id, application_period_id, beneficiary_status, parental_status, total_annual_family_income,
            house_status, special_consideration, reason_for_expecting_financial_assistance,
            have_failed_in_any_subject_in_last_2_sem, latest_sem_perc, previous_sem_perc,
            difference_in_sem_perc, current_semester, latest_sem_marksheet, previous_sem_marksheet,
            bonafide_or_fee_paid_proof
        )
        values(
            %(beneficiary_id)s, %(application_period_id)s, %(beneficiary_status)s, %(parental_status)s, %(total_annual_family_income)s,
            %(house_status)s, %(special_consideration)s, %(reason_for_expecting_financial_assistance)s,
            %(have_failed_in_any_subject_in_last_2_sem)s, %(latest_sem_perc)s, %(previous_sem_perc)s,
            %(difference_in_sem_perc)s, %(current_semester)s, %(latest_sem_marksheet)s, %(previous_sem_marksheet)s,
            %(bonafide_or_fee_paid_proof)s    
        );
    """    

    new_application: None = execute_sql_commands(sql, data)
    context.update({"message": "Application submitted sucessfully.", "message_type": "Success"})
    return templates.TemplateResponse("message.html", context)


# @router.post("/bank_details")
# async def create_bank_details(RedirectResponse("/application_success", status_code = status.HTTP_302_FOUND)
#     request: Request,
#     user: schemas.TokenData = Depends(get_current_beneficiary),
#     bank_details: schemas.BeneficiaryBankInfo = Form()
# ):
#     # Check the beneficiary already filled the bank details.

#     sql: str = """select 1 from beneficiary_bank_details where id = %(beneficiary_id)s;"""

#     previous_record = execute_sql_select_statement(
#         sql, {"beneficiary_id": user.id}, 
#         fetch_all = False
#     )

#     if previous_record:
#         return templates.TemplateResponse("message.html", {"request": request, "user": user, "message_type": "Error", "message": "Already Filled Bank Details."})

#     sql: str = """
#         insert into beneficiary_bank_details(
#             id, account_holder_name, account_number, ifsc_code,bank_name, 
#             branch, bank_address, phone_number, upi_id, passbook
#         )
#         values (
#             %(id)s, %(account_holder_name)s, %(account_number)s, %(ifsc_code)s, %(bank_name)s, 
#             %(branch)s, %(bank_address)s, %(phone_number)s, %(upi_id)s, %(passbook)s
#         );
#     """
#     # Read the passbook.
#     passbook_content: bytes = await bank_details.passbook.read()
    
#     vars = bank_details.model_dump(exclude = {"passbook"})
#     print(vars)
#     vars.update({"id": user.id, "passbook": passbook_content})

#     new_bank_details = execute_sql_commands(sql, vars)

#     return RedirectResponse("/financial_assistance_application", status_code = status.HTTP_302_FOUND)

