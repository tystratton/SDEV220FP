# Ty's Work
# 5/8/2025
# This file is the for the application and Flask server

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import psycopg2
from database.pipeline import get_all_appointments
from database.pipeline import get_all_users
from dotenv import load_dotenv
import os
from flask_bcrypt import Bcrypt
from datetime import datetime
import traceback

load_dotenv()

# Get database connection details from environment variables
db_host = os.getenv("DB_HOST", "localhost")
db_name = os.getenv("DB_NAME", "giftedgown")
db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASS")

# Fallback for local DB_PASSWORD if DB_PASS (from Docker) isn't set
if db_password is None:
    db_password = os.getenv("DB_PASSWORD")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key_for_testing")
bcrypt = Bcrypt(app)

# Database connection setup
conn = psycopg2.connect(
    host=db_host,
    database=db_name,
    user=db_user,
    password=db_password
)

cur = conn.cursor()

@app.route('/')
def index():
    return render_template('user.html')

@app.route('/admin')
def admin():
    print(f"Admin Route Session: {session}")
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to view this page', 'error')
        return redirect(url_for('admin_login'))
    
    try:
        appointments = get_all_appointments()
        print(f"Fetched {len(appointments)} appointments")
        return render_template('admin.html', appointments=appointments)
    except Exception as e:
        print(f"Error fetching appointments: {e}")
        flash('Error loading admin page data.', 'error')
        return "Error loading appointments", 500

@app.route('/submit', methods=['POST'])
def submit():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone = request.form['phone']
    appointment_time = request.form['datetime']  # combined date and time field
    event_type = request.form['type']
    gender_identity = request.form.get('gender_identity', '')
    notes = request.form.get('notes', '')

    # Combine first and last name from form into full_name for the database
    full_name = f"{first_name} {last_name}"

    cur.execute("""
        INSERT INTO appointments (full_name, email, phone, appointment_time, event_type, gender_identity, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (full_name, email, phone, appointment_time, event_type, gender_identity, notes))

    conn.commit()
    return redirect(url_for('thank_you'))

@app.route('/api/appointments/<int:appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Build dynamic update query based on provided fields
        update_fields = []
        update_values = []
        
        # Check which fields were provided and add them to update query
        field_mapping = {
            'first_name': None,  
            'last_name': None,   
            'full_name': 'full_name',
            'email': 'email',
            'phone': 'phone',
            'date': None,      
            'time': None,        
            'appointment_time': 'appointment_time',
            'event_type': 'event_type',
            'gender_identity': 'gender_identity',
            'notes': 'notes'
        }
        
        if 'first_name' in data or 'last_name' in data:
            # Get current full_name to modify just the part that changed
            cur.execute("SELECT full_name FROM appointments WHERE id = %s", (appointment_id,))
            current_name = cur.fetchone()
            
            if current_name:
                name_parts = current_name[0].split(' ', 1)
                current_first = name_parts[0] if len(name_parts) > 0 else ''
                current_last = name_parts[1] if len(name_parts) > 1 else ''
                
                new_first = data.get('first_name', current_first)
                new_last = data.get('last_name', current_last)
                
                data['full_name'] = f"{new_first} {new_last}"
        
        # Handle date + time => appointment_time
        if 'date' in data or 'time' in data:
            # Get current appointment_time to modify just the part that changed
            cur.execute("SELECT appointment_time FROM appointments WHERE id = %s", (appointment_id,))
            current_time = cur.fetchone()
            
            if current_time and current_time[0]:
                current_datetime = current_time[0]
                current_date = current_datetime.strftime('%Y-%m-%d')
                current_time_str = current_datetime.strftime('%H:%M:%S')
                
                new_date = data.get('date', current_date)
                new_time = data.get('time', current_time_str)
                
                data['appointment_time'] = f"{new_date} {new_time}"
        
        # Updated query
        for client_field, db_field in field_mapping.items():
            if client_field in data and db_field: 
                update_fields.append(f"{db_field} = %s")
                update_values.append(data[client_field])
        
        if update_fields:
            # Add appointment_id to values list
            update_values.append(appointment_id)
            
            # Update fields that have been provided
            update_query = f"""
                UPDATE appointments 
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id
            """
            
            cur.execute(update_query, update_values)
            updated_row = cur.fetchone()
            conn.commit()
            
            if updated_row:
                return jsonify({'success': True, 'message': f'Appointment {appointment_id} updated successfully'})
            else:
                return jsonify({'success': False, 'message': f'Appointment {appointment_id} not found'}), 404
        else:
            return jsonify({'success': False, 'message': 'No fields to update provided'}), 400
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Check if admin registration should be offered (only if no admins exist)
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = cur.fetchone()[0]
    show_admin_option = admin_count == 0

    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        register_as_admin_checked = request.form.get('register_as_admin') == 'true'

        # Determine role based on checkbox and re-verification of admin count
        role = 'user' # Default role
        if register_as_admin_checked and show_admin_option: # Use show_admin_option which reflects count *at time of POST*
             # Double-check admin count right before insert to be safe
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            current_admin_count = cur.fetchone()[0]
            if current_admin_count == 0:
                role = 'admin'
            else:
                # Edge case: an admin was created between page load and form submission
                flash('Admin already exists. Registering as regular user.', 'warning')
        
        # Check if user already exists (regardless of role check)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cur.fetchone() is not None:
            flash('Username already registered. Please log in.', 'error')
            # Pass the show_admin_option flag back even on failed registration attempt
            return render_template('register.html', show_admin_option=show_admin_option) 
        
        # Hash password
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Insert new user with determined role
        try:
            cur.execute("""
                INSERT INTO users (username, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (username, password_hash, role, datetime.now())) # Use the determined role
            
            new_user_id = cur.fetchone()[0] # Get the ID of the newly created user
            conn.commit()
            
            flash(f'Registration successful as {role}! Please log in.', 'success') # Notify user of their role

            # If registered as admin, log them in immediately and redirect to admin dashboard
            if role == 'admin':
                session['user_id'] = new_user_id
                session['username'] = username
                session['role'] = role
                flash('Admin registration successful! You are now logged in.', 'success') # Update flash message
                return redirect(url_for('admin'))
            else:
                # For regular users, redirect to the standard login page
                return redirect(url_for('login')) 

        except Exception as e:
            conn.rollback()
            flash(f'Registration failed: {str(e)}', 'error')
            # Need to pass the flag back on exception too
            return render_template('register.html', show_admin_option=show_admin_option)
    
    # GET request - render the registration form, passing the flag
    return render_template('register.html', show_admin_option=show_admin_option)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        
        # Check if user exists and password is correct
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user and bcrypt.check_password_hash(user[2], password):
            # Store user info in session
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            
            flash('Login successful!', 'success')
            
            # Redirect to admin page if admin, otherwise to user page
            if user[3] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    # GET request - render the login form
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear session data
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        
        # Check if user exists and password is correct
        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s AND role = 'admin'", (username,))
        user = cur.fetchone()
        
        if user and bcrypt.check_password_hash(user[2], password):
            # Store user info in session
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid admin credentials', 'error')
    
    # GET request - render the admin login form
    return render_template('admin_login.html')

@app.route('/admin/add', methods=['POST'])
def admin_add_appointment():
    print("--- Admin Add Appointment Route Hit ---")
    print(f"Session at start of add: {session}")
    
    # Check if admin is logged in
    if 'user_id' not in session or session.get('role') != 'admin':
        print("Admin check failed.")
        flash('Unauthorized action', 'error')
        # Redirect to admin login or handle appropriately
        return redirect(url_for('admin_login')) 

    try:
        print(f"Received form data: {request.form}")
        
        # Extract data from form
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        date_str = request.form['date']
        time_str = request.form['time']
        event_type = request.form['event_type']
        gender_identity = request.form.get('gender_identity', '') # Optional field
        notes = request.form.get('notes', '') # Optional field

        # Combine date and time strings into a format suitable for DB (assuming TIMESTAMP type)
        appointment_time_str = f"{date_str} {time_str}:00" # Add seconds if needed
        
        print("Executing DB insert...")
        cur.execute("""
            INSERT INTO appointments (full_name, email, phone, appointment_time, event_type, gender_identity, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (full_name, email, phone, appointment_time_str, event_type, gender_identity, notes))

        print("Committing transaction...")
        conn.commit()
        print("Commit successful.")
        flash('Appointment added successfully!', 'success')
    except Exception as e:
        conn.rollback()
        print(f"--- ERROR ADDING APPOINTMENT ---")
        print(f"Exception Type: {type(e)}")
        print(f"Exception Args: {e.args}")
        print(f"Traceback:")
        traceback.print_exc() # Print the full traceback
        print(f"--- END ERROR DETAILS ---")
        # Keep the original generic flash message for the user interface
        flash('Error adding appointment.', 'error')

    print("Redirecting to admin page.")
    return redirect(url_for('admin'))

@app.route('/admin/edit/<int:appointment_id>', methods=['POST'])
def admin_edit_appointment(appointment_id):
    # Check if admin is logged in
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized action', 'error')
        return redirect(url_for('admin_login'))

    try:
        # Extract data from form (similar to /admin/add, but for updating)
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        date_str = request.form['date']
        time_str = request.form['time']
        event_type = request.form['event_type']
        gender_identity = request.form.get('gender_identity', '')
        notes = request.form.get('notes', '')

        # Combine date and time
        appointment_time_str = f"{date_str} {time_str}:00"

        # Update the appointment in the database
        update_query = """
            UPDATE appointments
            SET full_name = %s, email = %s, phone = %s,
                appointment_time = %s, event_type = %s, gender_identity = %s, notes = %s
            WHERE id = %s
        """
        cur.execute(update_query, (
            full_name, email, phone, appointment_time_str,
            event_type, gender_identity, notes, appointment_id
        ))
        conn.commit()
        flash(f'Appointment {appointment_id} updated successfully!', 'success')

    except Exception as e:
        conn.rollback()
        print(f"--- ERROR UPDATING APPOINTMENT {appointment_id} ---")
        print(f"Exception Type: {type(e)}")
        print(f"Exception Args: {e.args}")
        print(f"Traceback:")
        traceback.print_exc()
        print(f"--- END ERROR DETAILS ---")
        flash('Error updating appointment.', 'error')

    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    # Check if admin is logged in
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized action', 'error')
        return redirect(url_for('admin_login'))

    try:
        # Execute DELETE SQL command
        cur.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
        conn.commit()
        flash(f'Appointment {appointment_id} deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        print(f"Error deleting appointment {appointment_id}: {e}")
        flash('Error deleting appointment', 'error')
    
    return redirect(url_for('admin'))
# New routes to get users and change user roles.
@app.route('/api/users', methods=['GET'])  
def api_get_users():
    try: 
        users = get_all_users()
        return jsonify(users=[{'username': u[0], 'role': u[1]} for u in users])
    except Exception as e: 
        return jsonify({'error': str(e)})
    
@app.route('/api/users/<string:username>/role', methods=['PUT'])
def api_change_user_role(username):
    try: 
        data = request.get_json()
        new_role = data.get('role')
        if new_role not in ['admin', 'user']:
            return jsonify({'error': 'Invalid role'})
        
        cur.execute("UPDATE users SET role = %s WHERE username = %s", (new_role, username))
        conn.commit()
        return jsonify({'message': f"Role changed for {username} to {new_role}"})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
