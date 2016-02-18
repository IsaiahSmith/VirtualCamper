from flask import Flask, redirect, render_template, url_for, request, session
import bcrypt
from bcrypt import hashpw
import pymssql
import csv
import datetime;

app = Flask(__name__)

# get SQL Server credentials. 
credential_file = open('credentials.txt', 'r')
server = credential_file.readline().strip()
username = credential_file.readline().strip()
password = credential_file.readline().strip()
dbname = credential_file.readline().strip()
print "db server:", server
print "db name:", dbname

# connect to the Micosoft SQL server
conn = pymssql.connect(server, username, password, dbname)
cursor = conn.cursor(as_dict=True)
#conn.close() # maybe we should close the connection at some point

# Session secret key
app.secret_key = 'F12Zr47j\3yX R~X@H!jmM]Lwf/,?KT'

@app.route("/")
def index():
    session.clear()
    sumSessionCounter()
    session['theme'] = 'css/default.css';
    return redirect("/login")

def sumSessionCounter():
  try:
    session['counter'] += 1
  except KeyError:
    session['counter'] = 1


@app.route("/login", methods=['GET', 'POST'])
def login_user():
    if(request.method == 'POST'):
        # clear session
        session.clear()
        # check db to see if it's valid
        username = request.form['username']
        password = request.form['password']
        
        cursor.execute("EXEC GetUserID @username='"+username+"'")
        id = cursor.fetchall()[0]['id']
        
        cursor.execute("EXEC GetSalt @id='"+str(id)+"'")
        salt = cursor.fetchall()[0]['Salt']
        hashedPass = bcrypt.hashpw(password.encode('utf-8'), salt.encode('utf-8'))
         
        query = "EXEC AttemptLogin @username='"+username+"',@password='"+hashedPass+"'"
        cursor.execute(query)
        results = cursor.fetchall()
        
        print results
        
        if len(results) > 1:
            print "ERROR: we have two users with the same username.  this should not happen ever since username is a primary key"
            return render_template("login.html", message="internal server error")
        elif results == [] or results[0]['password'] != hashedPass:
            print hashedPass, results
            return render_template("login.html", message="invalid username or password")
        else:
            # set the session variable
            session['name'] = results[0]['Fname']
            session['id'] = results[0]['id']
            session['isAdmin'] = str(results[0]['isAdmin'])
            if results[0]['colTheme'] == None:
                session['theme'] = 'css/default.css'
            else:
                setThemeSession(results[0]['colTheme']);
                
            return redirect("/attendance")
    else:
        session.clear()
        return render_template("login.html")
    


@app.route("/attendance", methods=['GET', 'POST'])
def attendance_page():
    sumSessionCounter()
    if request.method == 'POST':
        camper = request.form['string']
        camperArr = camper.split(", ")
        nameArr = camperArr[0].split(" ")
        fname = nameArr[0]
        lname = nameArr[1]
        tribe = camperArr[1]
        id = camperArr[2]
        date = datetime.datetime.today();
        cursor.execute("EXEC InsertAttending @date ='"+str(date)+"', @id ='"+id+"'")
        conn.commit();
        return fname + " " +lname + ", " + tribe
    else:
        cursor.execute("EXEC GetTodaysAttendance");
        results = cursor.fetchall();
        number = len(results);
        cursor.execute("EXEC GetNotHereToday");
        answer = cursor.fetchall();
        
        cursor.execute("EXEC GetAllCampers");
        all = cursor.fetchall();
        return render_template("attendance.html", attendance=results, notHereYet=answer, allCampers=all, count=number)
    
@app.route("/camperLeft", methods=['GET', 'POST'])
def camperLeft():
    if request.method == 'POST':
        id = request.form['id']
        date = datetime.datetime.today();
        cursor.execute("EXEC CamperLeft @date ='"+str(date)+"', @id ='"+id+"'")
        conn.commit();
        return "all good"

@app.route("/camperCameBack", methods=['GET', 'POST'])
def camperCameBack():
    if request.method == 'POST':
        id = request.form['id']
        date = datetime.datetime.today();
        cursor.execute("EXEC CamperCameBack @date ='"+str(date)+"', @id ='"+id+"'")
        conn.commit();
        return "all good"

@app.route("/archive", methods=['GET', 'POST'])
def archive_page():
    sumSessionCounter()
    if request.method == 'POST':
        nothing
    else:
        cursor.execute("EXEC GetArchivedAttendance");
        results = cursor.fetchall();
        return render_template("archive.html", attendance=results)

@app.route("/setAttendance", methods=['GET', 'POST'])
def setAttendance_page():
    sumSessionCounter()
    if request.method == 'POST':
        list = request.form['list']
        split = list.split(",");
        date = datetime.datetime.today();
        for id in split:
            cursor.execute("EXEC InsertAttending @date ='"+str(date)+"', @id ='"+id+"'")
            conn.commit();
        return redirect("/attendance")
    else:
        print session['isAdmin']
        if session['isAdmin'] == False:
            print session['isAdmin']
            return redirect("/notAdmin")
        else:
            cursor.execute("EXEC GetNotHereToday");
            results = cursor.fetchall();
            return render_template("setAttendance.html", list=results)

@app.route("/about")
def about_page():
    sumSessionCounter()
    return render_template("about.html")

@app.route("/contact")
def contact_page():
    sumSessionCounter()
    return render_template("contact.html")

@app.route("/setSchedule")
def setSchedule_page():
    sumSessionCounter()
    cursor.execute("EXEC GetCounselor")
    results = cursor.fetchall()
    return render_template("setSchedule.html", workers = results)

@app.route("/schedule", methods=['GET', 'POST'])
def schedule_page():
    sumSessionCounter()
    date = datetime.datetime.today();
    if(date.weekday() != 0):
        if(date.weekday() <= 4):
            date -= datetime.timedelta(days=date.weekday());
        if(date.weekday() == 5):
            date += datetime.timedelta(days=2);
        if(date.weekday() == 6):
            date += datetime.timedelta(days=1);
    print date
    cursor.execute("EXEC GetWorkSchedule @scheduleDate = '"+ str(date)+ "'");
    schedule = cursor.fetchall();
#     query += "@date="+datetime.today();
#     cursor.execute(query);
#     results = cursor.fetchall();
    return render_template("schedule.html", schedule = schedule)

@app.route("/settings")
def settings_page():
    sumSessionCounter()
    cursor.execute("EXEC GetThemes")
    results = cursor.fetchall()
    return render_template("settings.html", themes=results)
    
@app.route("/settingsPassword", methods=['GET', 'POST'])
def setPass():
    if request.method == 'POST':
        id = request.form['id']

        newPass = request.form['newPass']
        newSalt = str(bcrypt.gensalt())
        newHashed = bcrypt.hashpw(newPass.encode('utf-8'), newSalt)
        
        oldPass = request.form['oldPass']
        
        cursor.execute("EXEC GetSalt @id='"+id+"'")
        oldSalt = cursor.fetchall()[0]['Salt']
        oldHashedPass = bcrypt.hashpw(oldPass.encode('utf-8'), oldSalt.encode('utf-8'))
        
        cursor.execute("EXEC ChangePassword @newpass='"+newHashed+"',@newsalt='"+newSalt+"',@oldpass='"+oldHashedPass+"',@id='"+id+"',@result=''")
        ans = cursor.fetchall()[0]['result']
        conn.commit()
        return ans
    else:
        cursor.execute("EXEC GetThemes")
        results = cursor.fetchall()
        return render_template("settings.html", themes=results)
    
@app.route("/settingsReg", methods=['GET', 'POST'])
def regUser():
    if request.method == 'POST':
        username = request.form['username']
        fname = request.form['fname']
        lname = request.form['lname']
        isAdmin = request.form['isAdmin']

        password = request.form['pass']
        salt = str(bcrypt.gensalt())
        hashedPass = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        cursor.execute("EXEC RegisterUser @username='"+username
                       +"',@password='"+hashedPass
                       +"',@salt='"+salt
                       +"',@fname='"+fname
                       +"',@lname='"+lname
                       +"',@isAdmin='"+isAdmin
                       +"',@result=''")
        ans = cursor.fetchall()[0]['result']
        conn.commit()
        return ans
    else:
        cursor.execute("EXEC GetThemes")
        results = cursor.fetchall()
        return render_template("settings.html", themes=results)
    
@app.route("/settingsTheme", methods=['GET', 'POST'])
def setTheme():
    if request.method == 'POST':
        theme = request.form['theme']
        id = request.form['id']
        cursor.execute("EXEC SetTheme @theme='"+theme+"',@id='"+id+"'")
        conn.commit();
        setThemeSession(theme);
        return "all good"
    else:
        cursor.execute("EXEC GetThemes")
        results = cursor.fetchall()
        return render_template("settings.html", themes=results)

@app.route("/upload", methods=['GET', 'POST'])
def upload_page():
    sumSessionCounter()
    if request.method == 'POST':
        upload_file = request.files.get('file', default=None)
        if upload_file and allowed_file(upload_file.filename):
            print "we got a file!", dir(upload_file)
            for row in upload_file:
                row = row.split(',')
                fname = row[0]
                lname = row[1]
                tribe = row[2]
                print fname, lname, tribe
                query = "EXEC InsertCamper @Fname='"+fname+"',@Lname='"+lname+"',@Tribe='"+tribe+"'"
                print query
                cursor.execute(query)
            print "all done, committing"
            conn.commit()
            return "File uploaded successfully!" # a message for the javascript callback
        return "Oops! Something went wrong :( Try again"
    else: # it is a get request, return the webpage after rendering it
        return render_template("upload.html")

@app.route("/camperPage/<camperID>", methods=['GET', 'POST'])
def camper_page(camperID):
    sumSessionCounter()
    if request.method == 'POST':
        did = request.form['did']
        campID = request.form['camperID']
        eid = request.form['counsID']
        punish = request.form['punish']
        cursor.execute("EXEC InsertDiscipline @campID='"+campID+"',@EID='"+eid+"',@DID='"+did+"',@punish='"+punish+"'");
        return "all good"
    else:
        cursor.execute("EXEC GetCamperInfo @id ='"+camperID+"'");
        basic = cursor.fetchall();
        cursor.execute("EXEC GetCamperAllergies @id ='"+camperID+"'");
        allerg = cursor.fetchall();
        cursor.execute("EXEC GetCamperDiscipline @id ='"+camperID+"'");
        discp = cursor.fetchall();
        cursor.execute("EXEC GetAllCampers");
        all = cursor.fetchall();
        cursor.execute("EXEC GetAllDiscipline");
        allD = cursor.fetchall();
        return render_template("camperPage.html", basicInfo=basic, allCampers=all, allergies=allerg, discipline=discp, allDiscp=allD,id=camperID)

    
@app.route("/notFound")
def notFound_page():
    sumSessionCounter()
    return render_template("notFound.html")

@app.route("/notAdmin")
def notAdmin_page():
    sumSessionCounter()
    return render_template("notAdmin.html")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] == 'csv'

def setThemeSession(name):
    cursor.execute("EXEC GetSpecifiedTheme @theme='"+name+"'");
    themes = cursor.fetchall();
    session['theme'] = themes[0]['CSSName']


if __name__ == "__main__":
    app.debug = True # TODO: remove for production
    app.run(threaded=True)