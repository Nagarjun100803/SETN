import psycopg2 as pg
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor, RealDictRow, execute_values 
from typing import Any


# Connection parameters.
connection_params: dict[str, Any] = {
    # 'database': 'souglobal',
    'database': 'setn',
    'password': 'arju@123',
    'user': 'postgres', 
    'cursor_factory': RealDictCursor  
}

# Create a database pool to create and store the connections.
db: SimpleConnectionPool = SimpleConnectionPool(
    minconn = 4, maxconn = 12, **connection_params 
)

# conn: pg.extensions.connection =  pg.connect(**connection_params, cursor_factory = RealDictCursor)
# print(db)

def execute_sql_select_statement(
        sql: str, vars: dict | list | None = None,
        fetch_all: bool = True
) -> list[RealDictRow] | RealDictRow | None:
    
    # Get a connection from the pool. 
    conn: pg.extensions.connection = db.getconn()
    # Get a cursor object.
    cur: pg.extensions.cursor = conn.cursor()
    cur.execute(sql, vars = vars) # Execute the select statement.

    if fetch_all: 
        result: list[RealDictRow] | None = cur.fetchall() # Fetch all records.
    else:
        result: RealDictRow | None = cur.fetchone() # Fetch single record. 
    
    db.putconn(conn) # Release the connection back to the pool. 
    cur.close()

    return result




def execute_sql_commands(
        sql: str, vars: list | dict | None = None,  
        fetch: bool = False
) -> (RealDictRow | None):
    
    # Get the database connection. 
    conn: pg.extensions.connection = db.getconn()
    # Get the cursor object.
    cur = conn.cursor()
    # Execute the sql command/statemnt.
    cur.execute(sql, vars)
    # Commit the changes.
    conn.commit()
    # Release the connection back to the pool.
    db.putconn(conn)
    # if fetch = True, Need to fetch the record from the cursor.
    record = None
    if fetch:
        record: RealDictRow = cur.fetchone()
    cur.close()
    return record
   

def execute_sql_commands_with_multiple_params(
        sql: str, vars: list | dict, 
        template: dict,
) -> (RealDictRow | None):
    
    # Get the database connection. 
    conn: pg.extensions.connection = db.getconn()
    # Get the cursor object.
    cur = conn.cursor()
    # Execute the sql command/statemnt.
    execute_values(cur, sql, vars, template)
    # Commit the changes.
    conn.commit()
    # Close the cursor.
    cur.close()
    # Release the connection back to the pool.
    db.putconn(conn)
  


def initate_database_tables():
    tables: str = """

        create table if not exists courses(
            id serial primary key,
            course varchar not null, 
            degree varchar not null, 
            department varchar not null, 
            duration numeric not null
        );

        create table if not exists events(
            id serial primary key,
            title varchar not null,
            description varchar not null,
            start_date date not null,
            end_date date not null,
            place varchar,
            links varchar,
            posted_at timestamp not null default 'now()'

        );

        create table if not exists users(
            id serial primary key,
            role varchar(30) not null default 'beneficiary',
            username varchar(100) not null,
            email_id varchar(100) not null unique,
            password varchar not null,
            created_at timestamp not null default 'now()'
        );

        create table if not exists beneficiary_personal_details(
            id integer references users(id) not null, 
            full_name varchar not null, 
            name_as_in_passbook varchar not null, 
            gender varchar(20) not null, 
            gheru_naav varchar(30) not null, 
            aadhar_num varchar(12) not null, 
            date_of_birth date not null, 
            phone_num varchar(10) not null, 
            passport_size_pic bytea not null,

            remarks varchar,
            is_verified boolean not null default false,
            verified_by integer not null references users(id)
        );

        create table if not exists beneficiary_parental_details(
            id integer references users(id) not null,
            father_name varchar(100) not null,
            mother_name varchar(100) not null,
            father_occupation varchar(100) not null,
            mother_occupation varchar(100) not null,
            parent_phone_num varchar(10) not null,
            address_line varchar not null,
            city varchar(100) not null,
            district varchar(100) not null,
            pincode varchar(6) not null,
            family_pic bytea
        );

        create table if not exists beneficiary_educational_details(
            id integer references users(id) not null,
            tenth_perc numeric not null,
            eleventh_perc numeric not null,
            twelveth_perc numeric not null,
            course_id integer references courses(id) not null,
            college_name varchar not null,
            college_type varchar(30) not null,
            university varchar(100) not null,
            college_address varchar not null,
            tenth_marksheet bytea not null,
            eleventh_marksheet bytea,
            twelveth_marksheet bytea not null
        );

        create table if not exists beneficiary_bank_details(
            id integer references users(id) not null,
            account_holder_name varchar not null, 
            account_number varchar not null, 
            ifsc_code varchar not null,
            bank_name varchar not null, 
            branch varchar not null, 
            bank_address varchar not null,
            phone_number varchar not null,
            upi_id varchar not null, 
            passbook bytea not null   
        );

        create table if not exists application_periods(
            id serial primary key,
            academic_year varchar(30) not null,
            semester varchar(30) not null,
            start_date date not null,
            end_date date not null,
            opened_at timestamp not null default 'now()'
        );

        create table if not exists financial_assistance_applications(
            id serial primary key,
            beneficiary_id integer references users(id),
            application_period_id integer references application_periods(id) not null, 

            beneficiary_status varchar not null,
            parental_status varchar not null,
            total_annual_family_income varchar not null,
            house_status varchar not null,

            reason_for_expecting_financial_assistance varchar not null, 
            special_consideration text not null,
            have_failed_in_any_subject_in_last_2_sem boolean default 'false',

            latest_sem_perc numeric not null,
            previous_sem_perc numeric not null,
            difference_in_sem_perc numeric not null,
            current_semester numeric not null,
            
            latest_sem_marksheet bytea not null,
            previous_sem_marksheet bytea not null,
            bonafide_or_fee_paid_proof bytea,

            applied_at timestamp not null default 'now()',
            reason_for_rejection varchar,
            is_approved boolean,
            
            unique(beneficiary_id, application_period_id)
        );


        create table if not exists approved_applications(
            application_id integer references financial_assistance_applications(id) not null unique,
            sponsor_id integer references users(id),
            amount numeric,
            transfered_at timestamp,
            approved_by integer references users(id) not null,
            approved_at timestamp not null default 'now()'
        );

        create table if not exists beneficiary_assignments(
            beneficiary_id integer references users(id) not null,
            volunteer_id integer references users(id) not null,
            assigned_by integer references users(id) not null,
            assigned_at timestamp not null default 'now()',
            verification_status varchar default 'pending',
            verified_at timestamp

            --unique(beneficiary_id, volunteer_id)
        );
    """

    execute_sql_commands(tables)
    print('Tables Setup done.')
 
initate_database_tables()