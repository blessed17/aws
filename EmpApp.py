from time import time
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, date
from pymysql import connections
import pymysql
import botocore
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


@app.route("/addemp", methods=['GET', 'POST'])
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
            return render_template('GetEmpOutput.html', id=emp_id, fname=first_name, lname=last_name, interest=pri_skill, location=location)

@app.route("/")
def dashboard():
    return render_template('Dashboard.html')

@app.route("/getempout")
def getEmpOutput():
    return render_template('GetEmpOutput.html')


@app.route("/aboutus")
def aboutUs():
    return render_template('AboutUs.html')

@app.route("/khuweeming")
def khuWeeMing():
    return render_template('KhuWeeMing.html')

@app.route("/tanhaoyou")
def tanHaoYou():
    return render_template('TanHaoYou.html')

@app.route("/yekuanliang")
def yeKuanLiang():
    return render_template('YeKuanLiang.html')

@app.route("/displayemp", methods=['GET'])
def displayEmployee():
    cursor = db_conn.cursor()
    cursor.execute("Select * from employee")
    employeeList = cursor.fetchall()
    print(employeeList)
    return render_template('DisplayEmp.html', empList=employeeList, bucketName=bucket)

@app.route("/addedemp", methods=['POST'])
def AddedEmp():
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

        cursor.execute(insert_sql, (None, first_name,
                       last_name, pri_skill, location, None))

        db_conn.commit()

        sql_select_Query = "SELECT emp_id FROM employee ORDER BY emp_id DESC LIMIT 1"
        cursor = db_conn.cursor()
        cursor.execute(sql_select_Query)

        emp_id = cursor.fetchone()

        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + \
            str(emp_id[0]) + "_image_file" + \
            pathlib.Path(emp_image_file.filename).suffix

        update_sql = "UPDATE employee set img_url =(%s) where emp_id=(%s)"
        cursor.execute(update_sql, (emp_image_file_name_in_s3, str(emp_id[0])))
        db_conn.commit()

        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(
                Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client(
                's3').get_bucket_location(Bucket=custombucket)
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
    return redirect(url_for("displayEmployee"))


@app.route("/deleteemp", methods=['GET', 'POST'])
def deleteEmployee():

    # delete data in database
    cursor = db_conn.cursor()
    query = "DELETE FROM employee WHERE emp_id = %s"
    id = str(request.form['DeleteEmployee'])

    # delete image in S3 bucket
    mycursor = db_conn.cursor()
    myquery = "SELECT img_url FROM employee WHERE emp_id = %s"
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
    cursor.execute(query, emp_id)
    data = cursor.fetchall()
    cursor.close()
    print(data[0])
    return render_template('EditEmp.html', employee=data[0], bucketName=bucket)


@app.route("/updateemp/<id>", methods=['POST'])
def updateEmployee(id):
    if request.method == 'POST':
        emp_id = id
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        pri_skill = request.form['pri_skill']
        location = request.form['location']
        emp_image_file = request.files['emp_image_file']
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        if emp_image_file.filename == "":
            query = "UPDATE employee SET first_name=%s, last_name=%s, pri_skill=%s, location=%s WHERE emp_id=%s"
            query_item = (first_name, last_name, pri_skill, location, emp_id)
        else:
            # delete image in S3 bucket
            mycursor = db_conn.cursor()
            myquery = "SELECT img_url FROM employee WHERE emp_id = %s"
            mycursor.execute(myquery, id)
            img = str(mycursor.fetchall())
            img = img[3:-5]
            s3 = boto3.resource('s3')
            s3.Object(custombucket, img).delete()

            # Uplaod image file in S3 #
            emp_image_file_name_in_s3 = "emp-id-" + \
                str(emp_id) + "_image_file" + \
                pathlib.Path(emp_image_file.filename).suffix
            s3 = boto3.resource('s3')
            try:
                print("Data inserted in MySQL RDS... uploading image to S3...")
                s3.Bucket(custombucket).put_object(
                    Key=emp_image_file_name_in_s3, Body=emp_image_file)
                bucket_location = boto3.client(
                    's3').get_bucket_location(Bucket=custombucket)
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
            query_item = (first_name, last_name, pri_skill,
                          location, str(emp_image_file_name_in_s3), emp_id)
        cursor.execute(query, query_item)
        db_conn.commit()
        return redirect(url_for("displayEmployee"))


@app.route("/uploadfile", methods=['GET', 'POST'])
def uploadFile():
    return render_template('UploadFile.html')


@app.route("/uploadedfile", methods=['GET', 'POST'])
def uploadedFile():
    doc_name = request.form['docName']
    doc_url = request.files['emp_image_file']
    upload_date = datetime.now().strftime("%Y-%m-%d")    
    emp_id = request.form['empID']

    # ==================================================================================
    insert_sql = "INSERT INTO document VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if doc_url.filename == "":
        return "Please select a file"

    try:
        cursor.execute(insert_sql, (None, doc_name, None, upload_date, emp_id))
        db_conn.commit()

        sql_select_Query = "SELECT doc_id FROM document ORDER BY doc_id DESC LIMIT 1"
        cursor = db_conn.cursor()
        cursor.execute(sql_select_Query)

        doc_id = cursor.fetchone()

        # emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        upload_file_name_in_s3 = "uploadfile-id-" + \
            str(doc_id[0]) + "_image_file" + \
            pathlib.Path(doc_url.filename).suffix

        update_sql = "UPDATE document set doc_url =(%s) where doc_id=(%s)"
        cursor.execute(
            update_sql, (upload_file_name_in_s3, str(doc_id[0])))
        db_conn.commit()

        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(
                Key=upload_file_name_in_s3, Body=doc_url)
            bucket_location = boto3.client(
                's3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                upload_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    # ==================================================================================
    return redirect(url_for("displayDoc"))




@app.route("/displaydoc", methods=['POST', 'GET'])
def displayDoc():
    cursor = db_conn.cursor()
    cursor.execute("SELECT doc_id, doc_name, CONCAT(first_name, ' ', last_name),upload_date, doc_url FROM employee, document WHERE employee.emp_id = document.emp_id")
    documentList = cursor.fetchall()
    return render_template('DisplayFile.html', docList=documentList, bucketName=bucket)


@app.route("/displayleave", methods=['GET'])
def displayLeave():
    cursor = db_conn.cursor()
    cursor.execute("Select * from leaves")
    leaveList = cursor.fetchall()
    print(leaveList)
    return render_template('DisplayLeave.html', lveList=leaveList, bucketName=bucket)


@app.route("/viewleave/<id>", methods=['GET', 'POST'])
def viewLeave(id):
    leave_id = str(id)
    query = "SELECT * FROM leaves WHERE leave_id = %s"
    cursor = db_conn.cursor()
    cursor.execute(query, leave_id)
    data = cursor.fetchall()
    cursor.close()
    print(data[0])
    return render_template('ViewLeave.html', leaves=data[0], bucketName=bucket)


@app.route("/addleave", methods=['GET', 'POST'])
def addLeave():
    return render_template('AddLeave.html')


@app.route("/addedleave", methods=['GET', 'POST'])
def addedLeave():
    emp_id = request.form['emp_id']
    date_start = request.form['date_start']
    date_end = request.form['date_end']
    day_count = datetime.strptime(date_end, "%Y-%m-%d") - datetime.strptime(date_start, "%Y-%m-%d") + 1
    reason = request.form['reason']
    apply_date = datetime.now().strftime("%Y-%m-%d")

    insert_sql = "INSERT INTO leaves VALUES (%s,%s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(insert_sql, (None, emp_id, date_start,
                   date_end, day_count.days, reason, apply_date))
    db_conn.commit()
    cursor.close()
    return redirect(url_for("displayLeave"))


@app.route("/displayclaim", methods=['GET'])
def displayclaim():
    cursor = db_conn.cursor()
    cursor.execute("Select * from claim")
    claimList = cursor.fetchall()
    print(claimList)
    return render_template('DisplayClaim.html', clmList=claimList, bucketName=bucket)


@app.route("/viewclaim/<id>", methods=['GET', 'POST'])
def viewClaim(id):
    claim_id = str(id)
    query = "SELECT * FROM claim WHERE claim_id = %s"
    cursor = db_conn.cursor()
    cursor.execute(query, claim_id)
    data = cursor.fetchall()
    cursor.close()
    print(data[0])
    return render_template('ViewClaim.html', claim=data[0], bucketName=bucket)


@app.route("/addclaim", methods=['GET', 'POST'])
def addClaim():
    return render_template('AddClaim.html')


@app.route("/addedclaim", methods=['GET', 'POST'])
def addedClaim():
    emp_id = request.form['emp_id']
    date_from = request.form['date_from']
    date_to = request.form['date_to']
    claim_date = datetime.now().strftime("%Y-%m-%d")
    claim_amount = request.form['claim_amount']
    claim_reason = request.form['claim_reason']
    claim_evidence = request.files['claim_evidence']

    # ==================================================================================
    insert_sql = "INSERT INTO claim VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if claim_evidence.filename == "":
        return "Please select a file"

    try:
        cursor.execute(insert_sql, (None, emp_id, date_from,
                       date_to, claim_date, claim_amount, claim_reason, None))

        db_conn.commit()

        sql_select_Query = "SELECT claim_id FROM claim ORDER BY claim_id DESC LIMIT 1"
        cursor = db_conn.cursor()
        cursor.execute(sql_select_Query)

        claim_id = cursor.fetchone()

        # emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        claim_image_file_name_in_s3 = "claim-id-" + \
            str(claim_id[0]) + "_image_file" + \
            pathlib.Path(claim_evidence.filename).suffix

        update_sql = "UPDATE claim set claim_evidence =(%s) where claim_id=(%s)"
        cursor.execute(
            update_sql, (claim_image_file_name_in_s3, str(claim_id[0])))
        db_conn.commit()

        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(
                Key=claim_image_file_name_in_s3, Body=claim_evidence)
            bucket_location = boto3.client(
                's3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                claim_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    # ==================================================================================

    return redirect(url_for("displayclaim"))


@app.route("/addattendance", methods=['GET', 'POST'])
def addAttendance():
    return render_template('AddAttendance.html')


@app.route("/addedattendance", methods=['GET', 'POST'])
def addedAttendance():
    emp_id = request.form['emp_id']
    time_in = request.form['attd_time_in']
    time_out = request.form['attd_time_out']
    attd_date = request.form['attd_date']
    (h_time_in, m_time_in) = time_in.split(':')
    (h_time_out, m_time_out) = time_out.split(':')
    workingHour = (int(h_time_out) + int(m_time_out) / 60) - \
        (int(h_time_in) + int(m_time_in) / 60)

    if (int(h_time_in) >= 9 and int(m_time_in) > 0):
        status = "LATE"
    else:
        status = "ON TIME"

    insert_sql = "INSERT INTO attendance VALUES (%s,%s, %s, %s, %s, %s,%s)"
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(insert_sql, (None, attd_date, time_in,
                   time_out, workingHour, status, emp_id))
    db_conn.commit()
    cursor.close()
    return redirect(url_for("displayAttendance"))


@app.route("/displayattendance", methods=['GET', 'POST'])
def displayAttendance():
    cursor = db_conn.cursor()
    cursor.execute("SELECT atd_id, atd_date,atd_timeIn, atd_timeOut,atd_workingHour,atd_status, CONCAT(first_name, ' ', last_name) FROM employee, attendance WHERE employee.emp_id = attendance.emp_id")
    attendanceList = cursor.fetchall()
    return render_template('DisplayAttendance.html', attdList=attendanceList)


@app.route("/editattendance/<id>", methods=['GET', 'POST'])
def editAttendance(id):
    attd_id = str(id)
    query = "SELECT * FROM attendance WHERE atd_id = %s"
    cursor = db_conn.cursor()
    cursor.execute(query, attd_id)
    data = cursor.fetchall()
    cursor.close()
    timein = datetime.strptime(str(data[0][2]), "%H:%M:%S").time()
    return render_template('EditAttendance.html', attd=data[0], timeIn=timein)


@app.route("/updateattd/<id>", methods=['GET', 'POST'])
def updateAttendance(id):
    if request.method == 'GET':
        return redirect(url_for("displayAttendance"))
    else:
                
        attd_id = id
        time_in = request.form['time_in'][:5]
        time_out = request.form['time_out'][:5]
        date = request.form['date']
        (h_time_in, m_time_in) = time_in.split(':')
        (h_time_out, m_time_out) = time_out.split(':')
        workingHour = (int(h_time_out) + int(m_time_out) / 60) - (int(h_time_in) + int(m_time_in) / 60)

        if (int(h_time_in) >= 9 and int(m_time_in) > 0):
            status = "LATE"
        else:
            status = "ON TIME"

        query = "UPDATE attendance SET atd_date=%s, atd_timeIn=%s, atd_timeOut=%s, atd_workingHour=%s, atd_status=%s WHERE atd_id=%s"
        query_item = (date, time_in, time_out,workingHour, status, attd_id)
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, query_item)
        db_conn.commit()
        return redirect(url_for("displayAttendance"))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
