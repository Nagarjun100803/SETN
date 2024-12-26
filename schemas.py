from pydantic import BaseModel, EmailStr, constr
from typing import Literal
from datetime import date
from fastapi import UploadFile


class UserCreate(BaseModel):

    email_id: EmailStr 
    username: str 
    password: str 
    confirm_password: str 
    role: Literal['admin', 'beneficiary', 'volunteer', 'sponsor'] = 'beneficiary'

class TokenData(BaseModel):
    id: int 
    role: str

class BeneficiaryPersonalInfo(BaseModel):

    initial: str
    name: str 
    name_as_in_passbook: str 
    gender: Literal['Male', 'Female']
    gheru_naav: str
    aadhar_num: constr(min_length = 12, max_length = 12) 
    date_of_birth: date
    phone_num: constr(min_length = 10, max_length = 10)
    passport_size_pic: UploadFile


class BeneficiaryParentalInfo(BaseModel):
    
    father_name: str 
    mother_name: str 
    father_occupation: str = 'Silk Weaver'
    mother_occupation: str = 'Home Maker'
    parent_phone_num: constr(min_length = 10, max_length = 10)
    address_line: str 
    city: str 
    district: str 
    pincode: constr(min_length = 6, max_length = 6)
    family_pic: UploadFile



# class BeneficiaryEducationalInfo(BaseModel):

#     tenth_perc: float 
#     eleventh_perc: float 
#     twelveth_perc: float 
#     course: Literal['Engineering', 'Arts and Science']
#     degree: Literal['UG', 'PG', 'PhD']
#     department: Literal['Computer Science', 'Computer Application', 'Mathematics']
#     college_name: str 
#     college_type: Literal['Affiliated', 'Autonomous']
#     university: str
#     college_address: str

class BeneficiaryEducationalInfo(BaseModel):

    tenth_perc: float 
    eleventh_perc: float 
    twelveth_perc: float 
    course: str
    degree: Literal['UG', 'PG', 'PhD']
    department: str
    college_name: str 
    college_type: Literal['Affiliated', 'Autonomous']
    university: str
    college_address: str
    tenth_marksheet: UploadFile
    eleventh_marksheet: UploadFile
    twelveth_marksheet: UploadFile



# class FinancialAssistanceApplication(BaseModel):

#     beneficiary_status: Literal['Received Financial Assistance Before', 'Not Received Financial Assistance Before']
#     parental_status: Literal['Both Parents Alive', 'One Parent Alive', 'Both Parents Not Alive']
#     total_annual_family_income: Literal[
#         'Upto Rs 1,20,000', 'Greater than Rs 1,20,000 but less than or equal to Rs 2,40,000',
#         'Greater than Rs 2,40,000'
#     ]
#     house_status: Literal['Rental', 'Own', 'Leased']
#     special_consideration: Literal[
#         'Loss of Job of Breadwinner', 'Sudden Illness Requiring Unexpected expenses',
#         'Handicapped/Chronic Illness Requiring Expenses Regularly',
#         'Student Doing Part Time Work To Support Family',
#         'No Support From Relatives'                           
#         ]
#     reason_for_expecting_financial_assistance: str 
#     have_failed_in_any_subject_in_last_2_sem: bool

#     latest_sem_perc: float
#     previous_sem_perc: float
#     current_semester: int
    
class FinancialAssistanceApplication(BaseModel):

    beneficiary_status: str
    parental_status: str
    total_annual_family_income: str
    house_status: str
    # special_consideration: str

    reason_for_expecting_financial_assistance: str 
    special_consideration: list[str]
    have_failed_in_any_subject_in_last_2_sem: bool

    latest_sem_perc: float
    previous_sem_perc: float
    current_semester: int
    
    latest_sem_marksheet: UploadFile
    previous_sem_marksheet: UploadFile
    bonafide_or_fee_paid_proof: UploadFile


class PasswordResetRequesetSchema(BaseModel):

    email_id: EmailStr

class PasswordResetSchema(BaseModel):

    new_password: str 
    confirm_new_password: str 