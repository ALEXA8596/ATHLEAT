# import matplotlib.pyplot as plt
from flask import Flask, render_template, send_from_directory
from flask import request
import sqlite3
import hashlib
from helpers import login_required, generate_token
import base64
import os
import requests
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Now you can access environment variables using os.getenv()
app = Flask(__name__)

# Replace hardcoded API keys with environment variables
API_KEY = os.getenv('GOOGLEDEV')
client = OpenAI(api_key=os.getenv('OPENAI'))


app = Flask(__name__)

# Session DB stuff

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///users.db")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()

    if request.method == 'POST':
        # Get the form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        print(email, password)

        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))
        
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return "Invalid username and/or password"
        
        session["user_id"] = rows[0]["id"]
        return redirect("/app")


    if request.method =='GET':
        return render_template('login.html')
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # name, age, email, password, confirm_password, weight, height, profile_pic
        # try:

            
            name = request.form['name']
            username = request.form['username']
            age = request.form['age']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            weight = request.form['weight']
            height = request.form['height']
            profile_pic = request.files['profile_pic'].read()
            profile_pic = base64.b64encode(profile_pic).decode('utf-8')
            # if profile_pic:
            #     profile_pic = base64.b64encode(profile_pic.read()).decode('utf-8')

            print(name, username, age, email, password, confirm_password, weight, height, profile_pic)


            if (password != confirm_password):
                return "Passwords do not match, please try again."
            
            # In the future, change it so that they make a new token every time they sign in and make it expire every so often, 30 days?
            token = generate_token()

            # Check if the users table exists, if not create it
            db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    token TEXT NOT NULL,
                    weight REAL NOT NULL,
                    height REAL NOT NULL,
                    profile_pic TEXT NOT NULL
                )
            """)

            id = db.execute("""
                INSERT INTO users (name, username, age, email, hash, token, weight, height, profile_pic) 
                VALUES (:name, :username, :age, :email, :hash, :token, :weight, :height, :profile_pic)
            """, 
            name=name, username=username, age=age, email=email, hash=generate_password_hash(password), 
            token=token, weight=weight, height=height, profile_pic=profile_pic)

            print(id)

            return redirect('/login')

        # except Exception as e:
        #     return f"An error occurred: {e}"

    return render_template('register.html')


API_KEY = os.getenv('GOOGLEDEV')
VISION_URL = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
client= OpenAI(
  api_key=os.getenv('OPENAI')
)

def chatbot(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content": prompt}]
    )
    print(response.choices[0].message.content)
    response=response.choices[0].message.content
    return response



def detect_text(image_path):
    """Sends an uploaded image to Google Cloud Vision API for text detection."""
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode()

    image_data = {
        "requests": [{
            "image": {"content": base64_image},
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }

    response = requests.post(VISION_URL, json=image_data)

    # 🔹 Check for a successful request
    if response.status_code == 200:
        data = response.json()
        try:
            text = data["responses"][0]["textAnnotations"][0]["description"]
            return text
        except (KeyError, IndexError):
            return "No text detected."
    else:
        return f"Error {response.status_code}: {response.text}"


@app.route('/scanner', methods =['GET', 'POST'])
@login_required
def scanner():
  if request.method == "POST":
      if "file" not in request.files:
          return "No file uploaded."

      file = request.files["file"]
      if file.filename == "":
          return "No selected file."

      # Create uploads directory if it doesn't exist
      if not os.path.exists("uploads"):
          os.makedirs("uploads")
          
      # Save the file
      image_path = os.path.join("uploads", file.filename)
      file.save(image_path)

      # Process the image
      extracted_text = detect_text(image_path)
      ingredients = chatbot(f"You are given text that you need to clean up. Please only include the ingredients in the text after the word 'ingredients:' but do not include 'ingredients:' in your response. Here is the text: {extracted_text}")
      info = chatbot(f"You are a professional athletic advisor, and you are given a list of ingredients for a food. What are some of the health benefits of this food for atheletes and/or any health concerns? Is this good for atheletes? Please put it your beneficial information into greater than sign '>' singular bullet points. Here are the ingredients: {ingredients}")
      result = info.split(">")
      result.pop(0)
      print("hi")
      print(result)
      length = len(result)
      return render_template("scanner_uploaded.html", ingredients=ingredients, result=result, length=length)
  if request.method =="GET":
    return render_template("scanner.html")
    
@app.route('/app', methods=['GET'])
@login_required
def home():
    # Get user information from database using session user_id
    if "user_id" in session:
        user = db.execute("SELECT name FROM users WHERE id = ?", session["user_id"])
        if user:
            return render_template('app.html', username=user[0]["name"])
    return render_template('app.html', username="Guest")

@app.route("/specific", methods=["GET", "POST"])
@login_required
def specific():
    if request.method == "POST":
        ingredient = request.form.get("specific")
        response = chatbot(f"You are a professional atheletic advisor, and you are given an ingredients. What are some of the health benefits of this ingredient for atheletes and/or any health concerns? Is this good for atheletes? Please put it your beneficial information into greater than sign '>' singular bullet points. Here is the ingredient: {ingredient}")
        result = response.split(">")
        result.pop(0)
        length = len(result)
        return render_template("specific.html", ingredient=ingredient, result=result, length=length)

@app.route('/history', methods=['GET'])
@login_required
def history():
    # Get the activities from the database
    activities = db.execute("SELECT * FROM activities WHERE user_id = ?", session["user_id"])
    # make a copy of activites
    activitiesCopy = activities.copy()
    # go through each activity within activities and each of their keys
    # if it is none or undefined, set it to 0.
    # if the date is not given, remove the entire activity from the array
    
    for activity in activities:
        if activity["workout_date"] is None:
            activities.remove(activity)
        for key in activity.keys():
            if activity[key] is None or activity[key] == 'Undefined':
                activity[key] = 0

    print(activities)

     
    return render_template('history.html', activities=activitiesCopy, cleanedActivities=activities)

@app.route('/results', methods=['POST'])
@login_required
def results():
    activity_type = request.form.get('activity_type', request.form.get('other_activity'))
    duration = request.form.get('duration')
    distance = request.form.get('distance')
    calories_burnt = request.form.get('calories_burnt', "Not Given")
    strenuosity = request.form.get('strenuous_level')
    workout_time = request.form.get('workout_time')
    workout_date = request.form.get('activity_date')
    
    print(activity_type, duration, distance, calories_burnt, strenuosity, workout_time, workout_date)

    # Save the data to the database
    # if the activities array under the user doesn't exist, make one
    # if it does, append to it
    
    # if activites doesn't exist, create it

    db.execute("CREATE TABLE IF NOT EXISTS activities (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, activity_type TEXT, duration TEXT, distance TEXT, calories_burnt TEXT, strenuosity TEXT, workout_time TEXT, workout_date TEXT)")
    db.execute("INSERT INTO activities (user_id, activity_type, duration, distance, calories_burnt, strenuosity, workout_time, workout_date) VALUES (:user_id, :activity_type, :duration, :distance, :calories_burnt, :strenuosity, :workout_time, :workout_date)",
                user_id=session["user_id"], activity_type=activity_type, duration=duration, distance=distance, calories_burnt=calories_burnt, strenuosity=strenuosity, workout_time=workout_time, workout_date=workout_date)
    
    response = chatbot(f"You are a professional coach. You are given what an athlete did today. Here is the information: Activity Type: {activity_type}, Duration: {duration} minutes, Distance: {distance} mile(s), Calories Burnt: {calories_burnt}, Strenuosity: {strenuosity}, Workout Time: {workout_time}. Please provide feedback on how the athlete did today. Then, recommend recovery actions. Then, give a recipe suggestion for what to eat / drink / bake next in the form of a protein shake, protein bar, cookie, or other baked good. Also suggest a breakfast, lunch, or dinner based on the time.")
    return render_template('results.html', response=response, activity_type=activity_type, duration=duration, distance=distance, calories_burnt=calories_burnt, strenuosity=strenuosity, workout_time=workout_time, workout_date=workout_date)



@app.route('/workout', methods=['GET', 'POST'])
@login_required
def workout():
    if request.method =="POST":
        workout = request.form.get('workout')
        user_data = db.execute("SELECT weight, height, age FROM users WHERE id = ?", session["user_id"])
        if user_data:
            weight = user_data[0]["weight"]
            height = user_data[0]["height"]
            age = user_data[0]["age"]
        else:
            weight = height = age = None
        workout = chatbot(f"You are a professional athletic advisor. Create a workout with the given information. Weight is {weight}. Height is {height}. Age is {age}. This is what the person is looking for in their workout: {workout}. Put your workout steps into greater than sign '>' singular bullet points.")
        result = workout.split(">")
        result.pop(0)
        length = len(result)
        print(length)
        print("hi")
        return render_template('workout_results.html', result = result, length = length)
    else:
        return render_template('workout.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/settings')
#@login_required
def settings():
    return render_template('settings.html')


@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory('uploads', filename)


@app.route('/<path:filename>')
def send_css(filename):
    return send_from_directory('css', filename)

#@app.route('/<path:filename>')
#def send_static(filename):
    #return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, port=80)