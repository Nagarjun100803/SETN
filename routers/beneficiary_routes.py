from fastapi import APIRouter, Request, Response, Form, status, Depends
from config import templates
import schemas, utils
from database import execute_sql_select_statement, execute_sql_commands
from fastapi.responses import RedirectResponse
from oauth2 import get_current_beneficiary
from datetime import datetime, timedelta
import pandas as pd



router = APIRouter(tags = ['Beneficiary'])

start_date = datetime(2024, 12, 9) 
end_date = start_date + timedelta(20)


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


 
@router.get("/personal_details")
def get_personal_details_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary)
):
    context: dict = {"request": request, "user": user}
    # Check the user already applied the details.
    personal_details_sql: str = "select * from beneficiary_personal_details where id = %(id)s;"
    previous_record = execute_sql_select_statement(personal_details_sql, {"id": user.id}, fetch_all = False)

    if previous_record:
        context.update({"filled": True})
        return templates.TemplateResponse("personal_details.html", context)

    return templates.TemplateResponse("personal_details.html", context)



@router.get("/parental_details")
def get_parental_details_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary)
):
    context: dict = {"request": request, "user": user}
    #check the user already submited their details.
    parent_details_check_sql: str = """select * from beneficiary_parental_details where id = %(id)s;"""
    parent_details = execute_sql_select_statement(parent_details_check_sql, {'id': user.id}, fetch_all = False)

    if parent_details:
        context.update({"filled": True})
        return templates.TemplateResponse("parental_details.html", context)

    return templates.TemplateResponse("parental_details.html", context)




@router.get("/educational_details")
def get_educational_details_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary)
):
    context = {"request": request, "user": user}
    
    sql: str = "select * from beneficiary_educational_details where id = %(user_id)s;"
    previous_record = execute_sql_select_statement(sql, {'user_id': user.id}, fetch_all = False)

    if previous_record:
        context.update({"filled": True})
        templates.TemplateResponse("educational_details.html", context)

    course_list = get_course_list()
    context.update({"course": course_list})
    # print(context)
    return templates.TemplateResponse("educational_details.html", context)


@router.get("/financial_assistance_application")
def get_financial_assistance_application_page(
    request: Request,
    user: schemas.TokenData = Depends(get_current_beneficiary)
):
    
    existed_application_sql: str = """
            select 
                * 
            from 
                financial_assistance_applications 
            where 
               ((beneficiary_id = %(id)s) and (applied_at between %(start_date)s and %(end_date)s))
            ;
                
        """
    previous_application = execute_sql_select_statement(existed_application_sql, {"id": user.id, "start_date": start_date, "end_date": end_date}, fetch_all = False)
    # print(previous_application)
    if previous_application:
        # print(previous_application)
        return templates.TemplateResponse("application_form.html", {"request": request, "user": user, "applied": True})
    
    return templates.TemplateResponse("application_form.html", {"request": request, "user": user})



@router.get("/application_success")
def get_success_page(
    request: Request,    
    user: schemas.TokenData = Depends(get_current_beneficiary)
):
    context: dict = {"request": request, "user": user}
    return templates.TemplateResponse("success_application.html", context)

    



@router.post("/personal_details") 
async def create_personal_details(
    request: Request, response: Response,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    personal_details: schemas.BeneficiaryPersonalInfo = Form()    
):

    context: dict =  personal_details.model_dump() 
    context.update({"request": request})
    # Check the aadhar number. to identify duplicate record.
    aadhar_check_sql: str = "select * from beneficiary_personal_details where aadhar_num = %(aadhar_num)s; "
    previous_record = execute_sql_select_statement(
        aadhar_check_sql, vars = {'aadhar_num': personal_details.aadhar_num}, fetch_all = False
    )

    if previous_record:
        context.update({"error_message": "Aadhar number alreadys exists!"})
        return templates.TemplateResponse("personal_details.html", context)

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
                returning *
                ;     
            """
    new_personal_details: None = execute_sql_commands(sql, processed_data) 


    return RedirectResponse('/parental_details', status.HTTP_302_FOUND)  

    
@router.post("/parental_details")
async def create_parental_details(
    request: Request, response: Response,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    parental_details: schemas.BeneficiaryParentalInfo = Form()
):

    parent_details = parental_details.model_dump(exclude = {'family_pic'})
    # Standardize the data.
    processed_data: dict = utils.get_processed_data(parent_details)

    # Read the family_pic
    family_pic_content = await parental_details.family_pic.read()

    processed_data.update({'id': user.id, 'family_pic': family_pic_content})

    sql: str = """
            insert into 
                beneficiary_parental_details
            values(
                %(id)s, %(father_name)s, %(mother_name)s, %(father_occupation)s, %(mother_occupation)s,
                %(parent_phone_num)s, %(address_line)s, %(city)s, %(district)s, %(pincode)s, %(family_pic)s
            )
            returning *
            ;
    """
    new_parent_details: None = execute_sql_commands(sql, processed_data)

    return RedirectResponse("/educational_details", status.HTTP_302_FOUND)


    
    
@router.post("/educational_details")
async def create_educational_details(
    request: Request, response: Response,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    educational_details: schemas.BeneficiaryEducationalInfo = Form()
):

    data = educational_details.model_dump(exclude = {"tenth_marksheet", "eleventh_marksheet", "twelveth_marksheet", "degree"})
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
       returning id;
    """

    new_data: None = execute_sql_commands(sql, data)

    return RedirectResponse("/financial_assistance_application", status_code = status.HTTP_302_FOUND)

@router.post("/financial_assistance_application")
async def create_financial_assistance_form(
    request: Request, response: Response,
    user: schemas.TokenData = Depends(get_current_beneficiary),
    application_form: schemas.FinancialAssistanceApplication = Form()
):
    
    existed_application_sql: str = "select * from financial_assistance_applications where beneficiary_id = %(beneficiary_id)s and current_semester = %(current_semester)s;"
    existed_application = execute_sql_select_statement(existed_application_sql, {"beneficiary_id": user.id, "current_semester": application_form.current_semester}, fetch_all = False)

    if existed_application:
        return templates.TemplateResponse("application_form.html", {"request": request, "error_message": "Already applied for this semester."})
    
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
            beneficiary_id, beneficiary_status, parental_status, total_annual_family_income,
            house_status, special_consideration, reason_for_expecting_financial_assistance,
            have_failed_in_any_subject_in_last_2_sem, latest_sem_perc, previous_sem_perc,
            difference_in_sem_perc, current_semester, latest_sem_marksheet, previous_sem_marksheet,
            bonafide_or_fee_paid_proof
        )
        values(
            %(beneficiary_id)s, %(beneficiary_status)s, %(parental_status)s, %(total_annual_family_income)s,
            %(house_status)s, %(special_consideration)s, %(reason_for_expecting_financial_assistance)s,
            %(have_failed_in_any_subject_in_last_2_sem)s, %(latest_sem_perc)s, %(previous_sem_perc)s,
            %(difference_in_sem_perc)s, %(current_semester)s, %(latest_sem_marksheet)s, %(previous_sem_marksheet)s,
            %(bonafide_or_fee_paid_proof)s    
        )
        returning *
        ;
    """    

    new_application: None = execute_sql_commands(sql, data)

    return RedirectResponse("/application_success", status_code = status.HTTP_302_FOUND)

