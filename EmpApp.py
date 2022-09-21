from flask import Flask, render_template, request, redirect, url_for
from pymysql import connections
import pymysql
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

    insert_sql = "INSERT INTO employee VALUES (%s,%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (None,first_name, last_name, pri_skill, location,None))
 
        db_conn.commit()

        sql_select_Query = "SELECT emp_id FROM employee ORDER BY emp_id DESC LIMIT 1"
        cursor = db_conn.cursor()
        cursor.execute(sql_select_Query)

        emp_id = cursor.fetchone()

        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id[0]) + "_image_file"+pathlib.Path(emp_image_file.filename).suffix
        
        update_sql = "UPDATE employee set img_url =(%s) where emp_id=(%s)"
        cursor.execute(update_sql,(emp_image_file_name_in_s3,str(emp_id[0])))
        db_conn.commit()

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

@app.route("/displayemp", methods=['GET'])
def displayEmployee():
    cursor = db_conn.cursor()
    cursor.execute("Select * from employee")
    employeeList = cursor.fetchall()
    print(employeeList)
    return render_template('DisplayEmp.html', empList = employeeList, bucketName = bucket)

@app.route("/deleteemp", methods=['GET', 'POST'])
def deleteEmployee():

    # delete data in database
    cursor = db_conn.cursor()
    query = "DELETE FROM employee WHERE emp_id = %s"
    id = str(request.form['DeleteEmployee'])

    # delete image in S3 bucket
    mycursor = db_conn.cursor()
    myquery ="SELECT img_url FROM employee WHERE emp_id = %s"
    mycursor.execute(myquery, id)
    img = str(mycursor.fetchall())
    img = img[3:-5]
    s3 = boto3.resource('s3')
    s3.Object(custombucket, img).delete()    
    cursor.execute(query, id)

    db_conn.commit()  
    return redirect(url_for("displayEmployee"))

@app.route("/editemp/<id>", methods=['GET', 'POST'])
def editEmployee(id):
    emp_id = str(id)
    query = "SELECT * FROM employee WHERE emp_id = %s"
    cursor = db_conn.cursor() 
    cursor.execute(query,emp_id)
    data = cursor.fetchall()
    cursor.close()
    print(data[0])
    return render_template('EditEmp.html',employee = data[0], bucketName = bucket)  

@app.route("/updateemp/<id>", methods=['POST'])
def updateEmployee(id):
    if request.method =='POST':
        emp_id = id
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        pri_skill = request.form['pri_skill']
        location = request.form['location']
        emp_image_file = request.files['emp_image_file']
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)  
        if emp_image_file.filename == "":
            query = "UPDATE employee SET first_name=%s, last_name=%s, pri_skill=%s, location=%s WHERE emp_id=%s" 
            query_item = (first_name,last_name,pri_skill,location,emp_id)
        else:
            # delete image in S3 bucket
            mycursor = db_conn.cursor()
            myquery ="SELECT img_url FROM employee WHERE emp_id = %s"
            mycursor.execute(myquery, id)
            img = str(mycursor.fetchall())
            img = img[3:-5]
            s3 = boto3.resource('s3')
            s3.Object(custombucket, img).delete()

            # Uplaod image file in S3 #
            emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"+pathlib.Path(emp_image_file.filename).suffix
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
            query = "UPDATE employee SET first_name=%s, last_name=%s, pri_skill=%s, location=%s, img_url=%s WHERE emp_id=%s"  
            query_item = (first_name,last_name,pri_skill,location,str(emp_image_file_name_in_s3),emp_id)
        cursor.execute(query ,query_item)
        db_conn.commit()
        return redirect(url_for("displayEmployee"))

@app.route("/uploadfile", methods=['GET', 'POST'])
def uploadFile():        
    return render_template('UploadFile.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
