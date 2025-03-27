from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from extensions import db  # Import db from extensions.py
from models import User, Incident  # Import models
from flask_mail import Mail, Message

# Initialize the app and its configurations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus_security.db'
app.config['SECRET_KEY'] = 'your_secret_key'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'Thabilemkhize316@gmail.com'  # Your Gmail account
app.config['MAIL_PASSWORD'] = 'vlhtnbnuicbvefgh'  # Your generated App Password from Google

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize Flask-Mail
mail = Mail(app)


# Create all database tables
with app.app_context():
    db.create_all()

# Pre-create an admin user (if not already in database)
with app.app_context():
    admin = User.query.filter_by(email="admin@dut4life.ac.za").first()
    if not admin:
        admin = User(
            email="admin@dut4life.ac.za",
            password=generate_password_hash("admin123", method='pbkdf2:sha256'),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created with email: admin@dut4life.ac.za and password: admin123")
    else:
        print("Admin user already exists!")

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        
        # Validate email domain
        if not email.endswith("@dut4life.ac.za"):
            flash("Only DUT members can register with a @dut4life.ac.za email address", "error")
            return redirect(url_for('register'))

        # Register user with default role 'student'
        new_user = User(email=email, password=password, role='student')
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Hardcoded admin credentials
        if email == "admin@dut4life.ac.za" and password == "admin123":
            user = User.query.filter_by(email="admin@dut4life.ac.za").first()
            if user and user.role == 'admin':
                login_user(user)
                return redirect(url_for('admin_dashboard'))

        # Check database for regular users
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash("Invalid credentials", "error")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('dashboard.html')

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        incident_type = request.form['incident_type']
        description = request.form['description']

        # Create and save the new incident
        new_incident = Incident(
            user_id=current_user.id,
            incident_type=incident_type,
            description=description
        )
        db.session.add(new_incident)
        db.session.commit()

        # Send email to admin
        msg = Message(
            subject='New Incident Reported',
            sender='Thabilemkhize316@gmail.com',  # Use the DUT system email
            recipients=['22329286@dut4life.ac.za'],  # Admin email to receive the report
            body=f"""
            A new incident has been reported on DUT Campus Security Alert:

            - Incident Type: {incident_type}
            - Description: {description or 'N/A'}
            - Reported By: {current_user.email}

            Please log in to review the details and take necessary actions.
            """
        )
        mail.send(msg)

        flash("Incident reported successfully and an email has been sent to the admin.", "success")
        return render_template('confirmation.html', incident=new_incident, user_email=current_user.email)

    return render_template('report.html')


   
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    incidents = Incident.query.all()
    return render_template('admin.html', incidents=incidents)

@app.route('/history')
@login_required
def history():
    # Retrieve all incidents reported by the logged-in user
    incidents = Incident.query.filter_by(user_id=current_user.id).all()
    return render_template('history.html', incidents=incidents)

@app.route('/admin/delete/<int:incident_id>', methods=['POST'])
@login_required
def delete_incident(incident_id):
    if current_user.role != 'admin':  # Ensure only admins can delete incidents
        return redirect(url_for('dashboard'))

    # Find the incident by ID
    incident = Incident.query.get_or_404(incident_id)

    # Delete the incident
    db.session.delete(incident)
    db.session.commit()

    flash("Incident has been deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update/<int:incident_id>', methods=['GET', 'POST'])
@login_required
def update_incident(incident_id):
    if current_user.role != 'admin':  # Ensure only admins can update incidents
        return redirect(url_for('dashboard'))

    # Find the incident by ID
    incident = Incident.query.get_or_404(incident_id)

    if request.method == 'POST':
        # Update the incident details based on form data
        incident.incident_type = request.form['incident_type']
        incident.description = request.form['description']
        incident.status = request.form['status']
        db.session.commit()

        flash("Incident has been updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('update_incident.html', incident=incident)

@app.route('/map', methods=['GET'])
def map_page():
    return render_template('map.html', api_key="AIzaSyBllPxxnyKCluVGeT_GE7Bep8Gz4dblQ9Q")  # Pass your API key to the template

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update user profile information
        current_user.name = request.form['name']
        current_user.phone = request.form['phone']
        db.session.commit()  # Save changes to the database
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Render the profile page, passing the current user data to the template
    return render_template('profile.html', user=current_user)


@app.route('/confirmation')
def confirmation():
    # Ensure the timestamp is converted to ISO 8601 format before passing it to the template
    incident = {
        'incident_type': 'theft',  # Example data
        'description': None,
        'status': 'Pending',
        'timestamp': incident.timestamp.isoformat()  # Pass the timestamp in ISO format
    }
    return render_template('confirmation.html', incident=incident, user_email=current_user.email)



if __name__ == '__main__':
    app.run(debug=True)
