from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MySQL config (update with your credentials)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'cluster1'

mysql = MySQL(app)

# Helper: Check if first user exists

def is_first_user():
    cur = mysql.connection.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    count = cur.fetchone()[0]
    cur.close()
    return count == 0
@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT name, image_url FROM categories")
    categories = cur.fetchall()
    cur.close()
    return render_template('home.html', categories=categories, session=session)

@app.route('/sign', methods=['GET', 'POST'])
def sign():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM users WHERE email=%s', (email,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['email'] = user[1]
            session['role'] = user[3]
            flash('Signed in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('sign.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed = generate_password_hash(password)
        role = 'superadmin' if is_first_user() else 'user'
        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO users (email, password, role) VALUES (%s, %s, %s)', (email, hashed, role))
        mysql.connection.commit()
        cur.close()
        flash('Registration successful! Please sign in.', 'success')
        return redirect(url_for('sign'))
    return render_template('register.html')

@app.route('/payment')
def payment():
    return render_template('payment.html')

@app.route('/categories', methods=['GET', 'POST'])
def manage_categories():
    if 'user_id' not in session or session.get('role') not in ['admin', 'superadmin']:
        return redirect(url_for('sign'))
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name']
        image_url = request.form['image_url']
        cur.execute('INSERT INTO categories (name, image_url) VALUES (%s, %s)', (name, image_url))
        mysql.connection.commit()
    cur.execute('SELECT * FROM categories')
    categories = cur.fetchall()
    cur.close()
    return render_template('categories.html', categories=categories)

@app.route('/users')
def users():
    if 'user_id' not in session or session.get('role') != 'superadmin':
        return redirect(url_for('sign'))
    cur = mysql.connection.cursor()
    cur.execute('SELECT id, email, role FROM users')
    users = cur.fetchall()
    cur.close()
    return render_template('users.html', users=users)

@app.route('/assign_admin/<int:user_id>')
def assign_admin(user_id):
    if 'user_id' not in session or session.get('role') != 'superadmin':
        return redirect(url_for('sign'))
    cur = mysql.connection.cursor()
    cur.execute('UPDATE users SET role=%s WHERE id=%s', ('admin', user_id))
    mysql.connection.commit()
    cur.close()
    flash('User promoted to admin.', 'success')
    return redirect(url_for('users'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run()
