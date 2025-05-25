import base64
import os
from flask import Flask, render_template, request, redirect, url_for, Response, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = "your_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    streak = db.Column(db.Integer, default=0)
    last_posted = db.Column(db.DateTime)
    points = db.Column(db.Integer, default=0)

with app.app_context():
    db.drop_all()
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signin', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return redirect(url_for('signup'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = username
        return redirect(url_for('home'))
    return render_template('Signin/signin.html')

@app.route('/BeBetter')
def export_users():
    users = User.query.all()
    def generate():
        data = [['id', 'username', 'password', 'streak', 'points']]
        for user in users:
            data.append([user.id, user.username, user.password, user.streak, user.points])
        for row in data:
            yield ','.join(map(str, row)) + '\n'
    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=users.csv"})

@app.route('/home')
def home():
    top_users = User.query.order_by(User.streak.desc()).limit(10).all()
    return render_template('home/home.html', top_users=top_users)

@app.route('/events')
def events():
    return render_template('events/events.html')

@app.route('/post', methods=['GET', 'POST'])
def post():
    username = session.get('username', None)
    if not username:
        return redirect(url_for('signup'))

    user = User.query.filter_by(username=username).first()
    if not user:
        return redirect(url_for('signup'))

    message = ''
    streak = user.streak or 0

    if request.method == 'POST':
        image_data = request.form['image_data']
        header, encoded = image_data.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        filename = f'static/screenshot_{user.username}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.png'
        with open(filename, 'wb') as f:
            f.write(image_bytes)

        now = datetime.utcnow()
        gave_point = False

        if not user.last_posted or (now - user.last_posted) > timedelta(hours=24):
            user.streak = 1
            user.points += 1
            gave_point = True
            message = "Streak reset. Started a new streak! +1 point."
        elif (now - user.last_posted) > timedelta(hours=24):
            user.streak += 1
            user.points += 1
            gave_point = True
            message = f"Streak increased! Current streak: {user.streak} days. +1 point."
        else:
            message = "Already posted today. Streak unchanged. No extra point."

        user.last_posted = now
        db.session.commit()
        streak = user.streak

    return render_template('post/post.html', streak=streak, message=message, points=user.points)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
