from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash as gph
from werkzeug.security import check_password_hash as cph
from datetime import timedelta
import secrets
import MySQLdb
import html

app = Flask(__name__)
app.secret_key=secrets.token_urlsafe(16)
app.permanent_session_lifetime=timedelta(minutes=60)

def connect():
    con = MySQLdb.connect(host="localhost", user="root", passwd="chiffon0301", db="健康管理",  use_unicode=True,
        charset="utf8")
    return con

@app.route("/",methods=['GET', 'POST'])
def hello_world():
    return redirect("login")

@app.route("/make", methods=["GET", "POST"])
def make():
    if request.method == "GET":
        return render_template("make.html")
    elif request.method == "POST":
        email = request.form["email"]
        passwd = request.form["passwd"]
        name = request.form["name"]
        tel = request.form["tel"]
        hashpass=gph(passwd)
        con = connect()
        cur = con.cursor()
        cur.execute("""
                    SELECT * FROM list WHERE email=%(email)s
                    """,{"email":email})
        data=[]
        for row in cur:
            data.append(row)
        if len(data)!=0:
            return render_template("make.html", msg="既に存在するメールアドレスです")
        con.commit()
        con.close()
        con = connect()
        cur = con.cursor()
        cur.execute("""
                    INSERT INTO list
                    (email,passwd,tel,name)
                    VALUES (%(email)s,%(hashpass)s,%(tel)s,%(name)s)
                    """,{"email":email, "hashpass":hashpass, "tel":tel, "name":name})
        con.commit()
        con.close()
        return render_template("info.html", email=email, passwd=passwd, name=name, tel=tel)
    
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method =="GET":
        session.clear()
        return render_template("login.html")
    elif request.method =="POST":
        email=html.escape(request.form["email"])
        password=html.escape(request.form["passwd"])
        con = connect()
        cur = con.cursor()
        cur.execute("""
                    SELECT passwd,name,email,tel
                    FROM 健康管理.list
                    WHERE email=%(email)s
                    """,{"email":email})
        data=[]
        for row in cur:
            data.append([row[0],row[1],row[2],row[3]])
        if len(data)==0:
            con.close()
            return render_template("login.html",msg="メースアドレスが間違っています")
        if cph(data[0][0],password):
            session["name"]=data[0][1]
            session["email"]=data[0][2]
            session["tel"]=data[0][3]
            con.close()
            return redirect("/dashbord")
        else:
            con.close()
            return render_template("login.html",msg="パスワードが間違っています。")

@app.route("/home")
def home():
    if "name" in session:
        return render_template("succes.html",name=html.escape(session["name"]),email=html.escape(session["email"]),tel=html.escape(session["tel"]))
    else:
        return redirect("login")

from datetime import datetime

def calculate_bmi_info(height_cm, weight_kg):
    if not height_cm or height_cm == 0:
        return 0, "身長が入力されていません"
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    
    if bmi < 18.5:
        evaluation = "低体重（やせ型）"
    elif bmi < 25:
        evaluation = "普通体重"
    elif bmi < 30:
        evaluation = "肥満（1度）"
    else:
        evaluation = "肥満（2度以上）"
    
    return bmi, evaluation

@app.route("/dashbord", methods=["GET", "POST"])
def dashbord():
    
    if "email" not in session:
        return redirect("/login")
    
    email = session["email"]
    con = connect()
    cur = con.cursor()

    current_bmi = None
    current_evaluation = ""

    if request.method == "POST":
        try:
            weight = float(request.form["weight"])
            height = float(request.form["height"])
            current_bmi, current_evaluation = calculate_bmi_info(height, weight)
            
            cur.execute("""
                INSERT INTO weight_logs (email, weight, bmi, recorded_at) 
                VALUES (%(email)s, %(weight)s, %(bmi)s, %(date)s)
                """, {
                    "email": email, "weight": weight, "bmi": current_bmi, 
                    "date": datetime.now().strftime('%Y-%m-%d')
                })
            con.commit()
        except ValueError:
            pass

    cur.execute("""
                SELECT recorded_at, weight, bmi 
                FROM weight_logs 
                WHERE email=%(email)s 
                ORDER BY recorded_at ASC
                """, {"email": email})
    
    rows = cur.fetchall()
    
    if rows:
        latest_record = rows[-1]
        if not current_bmi:
            current_bmi = latest_record[2]
            
            _, current_evaluation = calculate_bmi_info(1, 1)
            
            cur.execute("SELECT height FROM list WHERE email=%s", (email,))
            
            _, current_evaluation = calculate_bmi_info(170, current_bmi * (1.7**2))

    dates = [row[0].strftime("%m/%d") for row in rows]
    weights = [row[1] for row in rows]
    bmis = [row[2] for row in rows]
    cur.execute("SELECT target_weight FROM list WHERE email=%s", (email,))
    row = cur.fetchone()
    target_weight = row[0] if row and row[0] else 0

    con.close()
    return render_template("dashbord.html", 
                           name=session.get("name"), 
                           email=email,
                           bmi=current_bmi, 
                           evaluation=current_evaluation,
                           target_weight=target_weight,
                           dates=dates, weights=weights, bmis=bmis)

@app.route("/update_target", methods=["POST"])
def update_target():
    if "email" not in session:
        return redirect("/login")
    

    target = request.form.get("target_weight")
    
    con = connect()
    cur = con.cursor()
    
    cur.execute("UPDATE list SET target_weight=%s WHERE email=%s", (target, session["email"]))
    con.commit()
    con.close()
    
    return redirect("/dashbord")

if __name__ == "__main__":
    app.run(host="0.0.0.0")