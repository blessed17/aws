from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
import pathlib
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template('AddEmp.html')


@app.route("/getemp", methods=['GET', 'POST'])
def getEmp():
    if request.method == 'GET':
        return render_template('GetEmp.html')
    else:
               
          emp_id = request.form['emp_id']

          insert_sql = "SELECT * FROM employee where emp_id = (%s)"
          cursor = db_conn.cursor()
          try: 
                cursor.execute(insert_sql, (emp_id))
                # db_conn.commit()
                records = cursor.fetchall()
                for row in records:
                    emp_id = row[0]
                    first_name = row[1]
                    last_name = row[2]
                    pri_skill = row[3]
                    location = row[4]

          finally:             
                cursor.close()
                print("Get data...")
                return render_template('GetEmpOutput.html', id=emp_id,fname=first_name,lname=last_name,interest=pri_skill,location=location)

@app.route("/getempout")
def getEmpOutput():
    return render_template('GetEmpOutput.html')


@app.route("/about")
def about():
    return render_template('www.intellipaat.com')


@app.route("/addemp", methods=['POST'])
def AddEmp():
    # emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO employee VALUES (%s,%s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (None,first_name, last_name, pri_skill, location))
        db_conn.commit()

        sql_select_Query = "SELECT emp_id FROM employee ORDER BY emp_id DESC LIMIT 1"
        cursor = db_conn.cursor()
        cursor.execute(sql_select_Query)

        emp_id = cursor.fetchone()

        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id[0]) + "_image_file"+pathlib.Path(emp_image_file.filename).suffix
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)

<<<<<<< Updated upstream
=======
@app.route("/displayemp", methods=['GET'])
def displayEmployee():
    cursor = db_conn.cursor()
    cursor.execute("Select * from employee")
    employeeList = cursor.fetchall()
    print(employeeList)
    return render_template('DisplayEmp.html', empList = employeeList, bucketName = bucket)

@app.route("/deleteemp", methods=['GET', 'POST'])
def deleteEmployee():
    cursor = db_conn.cursor()
    query = "DELETE FROM employee WHERE emp_id = %s"
    id = str(9)
    cursor.execute(query, id)
    db_conn.commit()        
    #return render_template('DisplayEmp.html', empList = employeeList, bucketName = bucket)

@app.route("/editemp")
def editEmployee():
     return render_template('EditEmp.html')  
>>>>>>> Stashed changes

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
