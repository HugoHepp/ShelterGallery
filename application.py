import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.utils import secure_filename
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
import pathlib

from helpers import apology, login_required, usd

# Configure application
app = Flask(__name__)

# Configure upload for pet pictures
UPLOAD_FOLDER = 'C:/Users/Hugo/Desktop/flaskproject/static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///database.db")

# Home page
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        # Query cities in database for the form
        datacity = db.execute("SELECT DISTINCT city FROM pets JOIN shelter ON pets.shelter_id = shelter.id ORDER BY city DESC")
        lenghtcity = len(datacity)
        return render_template("index.html", lenghtcity = lenghtcity, datacity = datacity)
    else:
        # Get info from the form
        tmpcity = request.form.get("city")
        tmpspecies = request.form.get("species")
        speciestitle = tmpspecies.upper()
        speciestext = tmpspecies.lower()
        # Find the animals in database
        dataquote = db.execute("SELECT * FROM pets JOIN shelter ON pets.shelter_id = shelter.id WHERE city = :city AND species = :species", city = tmpcity, species = tmpspecies)
        lenght = len(dataquote)

        # Return result of query
        return render_template("quote.html", dataquote=dataquote , lenght=lenght , species=tmpspecies, speciestitle = speciestitle, speciestext = speciestext)

# Informative pages
@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")




# Shelter personnal page to manage animals
@app.route("/myaccount")
@login_required
def myaccount():

    user_id = session["user_id"]
    datapet = db.execute("SELECT * FROM pets WHERE shelter_id = :user_id", user_id = user_id)
    lenght = len(datapet)
    petisempty =  len(db.execute("SELECT name FROM pets WHERE shelter_id = :user_id", user_id = user_id))
    return render_template("myaccount.html", petisempty = petisempty, datapet = datapet, lenght = lenght)


# Create profile for animal
@app.route("/createprofile", methods=["GET", "POST"])
@login_required
def createprofile():
    if request.method == "GET":
        return render_template("createprofile.html")
    else:

        # Get info from form
        tmpspecies = request.form.get("species")
        tmpname = request.form.get("name")
        tmpname = tmpname.title()
        tmpbirth = request.form.get("birth")
        tmpsexe = request.form.get("sexe")
        user_id = session["user_id"]

        # Check if all fields are completed
        if tmpname == "" or tmpbirth == "":
            flash('You must complete all fields')
            return redirect("/createprofile")


        # Code for upload file from the flask documentation : https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/

         # check if the post request has the file part
        if 'file' not in request.files:
            flash('You must provide a picture')
            return redirect("/createprofile")
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('You must provide a picture')
            return redirect("/createprofile")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Rename uploaded file with name of the animal and id of his shelter
            filename, file_extension = os.path.splitext(filename)
            filename = str(user_id) + tmpname + str(file_extension)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))


        # Endcode of upload code
        # Create profile in db
        db.execute("INSERT INTO pets(shelter_id, species, name, birth, sexe, picture) VALUES (:user_id, :tmpspecies, :tmpname, :tmpbirth, :tmpsexe, :picture)", user_id = user_id, tmpspecies = tmpspecies, tmpname = tmpname, tmpbirth = tmpbirth, tmpsexe = tmpsexe, picture = filename)
        return redirect("myaccount")

# Delete profile of animal page
@app.route("/deleteprofile", methods=["GET", "POST"])
@login_required
def deleteprofile():

    # Get list of shelter's registered animals
    user_id = session["user_id"]
    if request.method == "GET":
        datapet = db.execute("SELECT * FROM pets WHERE shelter_id = :user_id", user_id = user_id)
        lenght = len(datapet)
        return render_template("deleteprofile.html",datapet = datapet, lenght = lenght)

    else:
        # Get info from form
        tmpdelname = request.form.get("name")
        # Get name of picture to delete it
        nametodel = db.execute("SELECT picture FROM pets WHERE shelter_id = :user_id AND name = :tmpdelname", tmpdelname = tmpdelname, user_id = user_id)
        # Store the path in variable
        pathtodel = "static\\img\\"+ nametodel[0]["picture"]
        # Remove the picture
        os.remove(pathtodel)
        # Delete the animal from the database
        db.execute("DELETE FROM pets WHERE name = :tmpdelname AND shelter_id = :user_id ", tmpdelname = tmpdelname, user_id = user_id)
        return redirect("myaccount")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM shelter WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("myaccount")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("myaccount")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        #Safety check for inputs
        if not request.form.get("username"):
            return apology("Invalid username")

        elif not request.form.get("password"):
            return apology("Invalid password")

        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("Passwords don't match")

        username = request.form.get('username')

        mail = request.form.get('mail')
        mail = mail.capitalize()

        city = request.form.get('city')
        city = city.title()

        state = request.form.get('state')
        state = state.title()

        phone = request.form.get('phone')

        website = request.form.get('website')
        website = website.capitalize()


        #Check database for doublons
        checkname =  db.execute("SELECT username FROM shelter WHERE username = :username",username = request.form.get('username'))
        if len(checkname) != 0:
            return apology("Username already taken..")

        #Create account
        else:
            password = generate_password_hash(request.form.get('password'))
            db.execute("INSERT INTO shelter (username, hash, mail, city, state, phone, website) VALUES (:username, :password, :mail, :city, :state, :phone, :website)", username = username, password = password, mail = mail, city = city, state = state, phone = phone, website = website)
            return redirect("myaccount")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

# Check extension for upload pictures (from flask documentation : https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
