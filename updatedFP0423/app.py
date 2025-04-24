from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from flask_bcrypt import Bcrypt
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key_for_testing")
bcrypt = Bcrypt(app)

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="giftedgown",
    user="postgres",
    password=os.getenv("DB_PASSWORD")
)

# for testing as was having issues with registering user loading into database
def create_default_admin():
    cur.execute("SELECT * FROM users WHERE username = %s", ('admin@giftedgown.com',))
    if not cur.fetchone():
        password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
        cur.execute("""
            INSERT INTO users (username, password_hash, role, created_at)
            VALUES (%s, %s, %s, %s)
        """, ('admin@giftedgown.com', password_hash, 'admin', datetime.now()))
        conn.commit()
        print("Default admin user created: admin@giftedgown.com / admin123")
    else:
        print("Default admin already exists.")

conn = psycopg2.connect(
    host="localhost",
    database="giftedgown",
    user="postgres",
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()

# Optional auto-create admin user
# This can be deleted - debugging only as was having pscopg2 errors
try:
    create_default_admin()
except psycopg2.errors.UndefinedTable:
    print("'users' table does not exist yet. Skipping admin creation.")



@app.route('/')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
       return redirect(url_for('admin_login'))

    cur.execute("SELECT * FROM appointments ORDER BY appointment_time")
    appointments = cur.fetchall()
    return render_template('admin.html', appointments=appointments)

@app.route('/add', methods=['POST'])
def add_appointment():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('admin_login'))

    full_name = request.form['full_name']
    email = request.form['email']
    phone = request.form['phone']
    date = request.form['date']
    time = request.form['time']
    appointment_time = f"{date} {time}"
    event_type = request.form['event_type']
    gender_identity = request.form.get('gender_identity', '')
    notes = request.form.get('notes', '')

    cur.execute("""
        INSERT INTO appointments (full_name, email, phone, appointment_time, event_type, gender_identity, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (full_name, email, phone, appointment_time, event_type, gender_identity, notes))
    conn.commit()

    return redirect(url_for('admin'))

@app.route('/edit/<int:id>', methods=['POST'])
def edit_appointment(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('admin_login'))

    full_name = request.form['full_name']
    email = request.form['email']
    phone = request.form['phone']
    date = request.form['date']
    time = request.form['time']
    appointment_time = f"{date} {time}"
    event_type = request.form['event_type']
    gender_identity = request.form.get('gender_identity', '')
    notes = request.form.get('notes', '')

    cur.execute("""
        UPDATE appointments
        SET full_name = %s, email = %s, phone = %s, appointment_time = %s,
            event_type = %s, gender_identity = %s, notes = %s
        WHERE id = %s
    """, (full_name, email, phone, appointment_time, event_type, gender_identity, notes, id))
    conn.commit()

    return redirect(url_for('admin'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_appointment(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('admin_login'))

    cur.execute("DELETE FROM appointments WHERE id = %s", (id,))
    conn.commit()
    return redirect(url_for('admin'))

@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']

        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            flash('Username already registered. Please log in.', 'error')
            return redirect(url_for('admin_login'))

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        cur.execute("""
            INSERT INTO users (username, password_hash, role, created_at)
            VALUES (%s, %s, %s, %s)
        """, (username, password_hash, 'admin', datetime.now()))
        conn.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('admin_login'))

    return render_template('admin_register.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']

        cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        print("Submitted password:", password)
        print("Stored hash:", user[2])
        print("Password match:", bcrypt.check_password_hash(user[2], password))


        if user and bcrypt.check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            flash('Login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    # Next 3 lines can be removed, inserted to check my returns trying to debug database link
    print("Registered Flask routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint:20s} → {rule.rule}")
    app.run(debug=True)

