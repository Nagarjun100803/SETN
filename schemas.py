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


class BeneficiaryBankInfo(BaseModel):
    
    account_holder_name: str 
    account_number: str 
    ifsc_code: str
    bank_name: str 
    branch: str 
    bank_address: str
    phone_number: str
    upi_id: str 
    passbook: UploadFile


class ApplicationPeriod(BaseModel):
    academic_year: str
    semester:  Literal['odd', 'even']
    start_date: date 
    end_date: date    
     
class FinancialAssistanceApplication(BaseModel):

    application_period_id:int
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

class RemarksSchema(BaseModel):
    remarks: str 


class ApplicationFilterParams(BaseModel):
    email_id: str = ""
    name: str = ""
    semester: int | None = None
    beneficiary_status: str = ""
    college_name: str = ""
    location: str = ""
    course: str = ""

