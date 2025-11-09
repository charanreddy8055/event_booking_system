from flask import Flask, render_template, request, jsonify, session, redirect
import mysql.connector
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------------- DATABASE CONFIG ----------------------
DB_CONFIG = dict(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="Charan123@",
    database="event_booking_db"
)

def db():
    """Connect to the MySQL database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"❌ MySQL Connection Error: {err}")
        return None

# ---------------------- FRONTEND ROUTES ----------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/organizer')
def organizer_page():
    if session.get('role') != 'organizer':
        return redirect('/')
    return render_template('organizer_dashboard.html')

@app.route('/admin')
def admin_page():
    if session.get('role') != 'admin':
        return redirect('/')
    return render_template('admin_dashboard.html')

@app.route('/my-bookings')
def my_bookings_page():
    if 'uid' not in session:
        return redirect('/')
    return render_template('my_bookings.html')

# ---------------------- AUTH ROUTES ----------------------

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    conn = db()
    if not conn:
        return jsonify(message="Database connection failed"), 500

    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (data["email"], data["password"]))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify(message="Invalid credentials"), 401

    session['uid'] = user['id']
    session['role'] = user['role']
    session['name'] = user['name']
    session['email'] = user['email']

    response_data = {
        'message': f"{user['role'].title()} login successful",
        'user_id': user['id'],
        'name': user['name'],
        'role': user['role'],
        'email': user['email']
    }

    if user['role'] == 'admin':
        response_data['redirect'] = '/admin'
    elif user['role'] == 'organizer':
        response_data['redirect'] = '/organizer'
    else:
        response_data['redirect'] = '/'

    return jsonify(response_data)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    conn = db()
    if not conn:
        return jsonify(message="Database connection failed"), 500

    try:
        cur = conn.cursor()
        
        # Get role from request, default to 'user' if not provided
        role = data.get('role', 'user')
        
        # Validate role
        if role not in ['user', 'organizer']:
            role = 'user'
            
        cur.execute("INSERT INTO users(name,email,password,role) VALUES(%s,%s,%s,%s)",
                    (data['name'], data['email'], data['password'], role))
        conn.commit()
        cur.close()
        conn.close()
        
        role_message = "User" if role == 'user' else "Organizer"
        return jsonify(message=f"✅ {role_message} account created successfully! You can now login.")
        
    except mysql.connector.Error as err:
        if err.errno == 1062:  # Duplicate entry
            return jsonify(message="❌ Email already exists"), 400
        return jsonify(message="❌ Registration failed"), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------------- EVENT ROUTES ----------------------

@app.route('/api/events')
def get_events():
    conn = db()
    if not conn:
        return jsonify([])

    cur = conn.cursor(dictionary=True)
    
    # Try with booking_status first, then fallback
    try:
        cur.execute("""
            SELECT e.*, 
                   (e.seats - COALESCE((SELECT COUNT(*) FROM bookings WHERE event_id = e.id AND booking_status='confirmed'), 0)) as available_seats
            FROM events e 
            WHERE e.status='approved' AND e.date >= CURDATE()
            ORDER BY e.date
        """)
    except mysql.connector.Error as e:
        # If booking_status column doesn't exist, use the old query
        print("⚠️ booking_status column not found, using fallback query")
        cur.execute("""
            SELECT e.*, 
                   (e.seats - COALESCE((SELECT COUNT(*) FROM bookings WHERE event_id = e.id), 0)) as available_seats
            FROM events e 
            WHERE e.status='approved' AND e.date >= CURDATE()
            ORDER BY e.date
        """)
    
    events = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(events)

@app.route('/api/organizer/events')
def organizer_events():
    if session.get('role') != 'organizer':
        return jsonify(message="Unauthorized"), 403

    conn = db()
    if not conn:
        return jsonify([])

    cur = conn.cursor(dictionary=True)
    
    # Try with booking_status first, then fallback
    try:
        cur.execute("""
            SELECT e.*, 
                   (SELECT COUNT(*) FROM bookings WHERE event_id = e.id AND booking_status='confirmed') as bookings_count
            FROM events e 
            WHERE e.organizer_id=%s 
            ORDER BY e.created_at DESC
        """, (session['uid'],))
    except mysql.connector.Error:
        cur.execute("""
            SELECT e.*, 
                   (SELECT COUNT(*) FROM bookings WHERE event_id = e.id) as bookings_count
            FROM events e 
            WHERE e.organizer_id=%s 
            ORDER BY e.created_at DESC
        """, (session['uid'],))
        
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)

@app.route('/api/organizer/create', methods=['POST'])
def organizer_create():
    if session.get('role') != 'organizer':
        return jsonify(message="Unauthorized"), 403

    data = request.get_json()
    conn = db()
    if not conn:
        return jsonify(message="Database connection failed"), 500

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO events(title, description, date, location, seats, organizer_id, status)
            VALUES(%s, %s, %s, %s, %s, %s, 'pending')
        """, (
            data['title'], 
            data['description'], 
            data['date'], 
            data['location'], 
            int(data['seats']), 
            session['uid']
        ))
        conn.commit()
        event_id = cur.lastrowid
        cur.close()
        conn.close()
        
        return jsonify(
            message="✅ Event created successfully and pending admin approval!",
            event_id=event_id
        )
        
    except Exception as e:
        return jsonify(message=f"Error creating event: {str(e)}"), 500

@app.route('/api/organizer/update', methods=['POST'])
def organizer_update_event():
    if session.get('role') != 'organizer':
        return jsonify(message="Unauthorized"), 403

    data = request.get_json()
    conn = db()
    if not conn:
        return jsonify(message="Database connection failed"), 500

    try:
        cur = conn.cursor()
        # Check if event belongs to this organizer
        cur.execute("SELECT id FROM events WHERE id=%s AND organizer_id=%s", 
                   (data['event_id'], session['uid']))
        event = cur.fetchone()
        
        if not event:
            return jsonify(message="Event not found or unauthorized"), 404

        cur.execute("""
            UPDATE events 
            SET title=%s, description=%s, date=%s, location=%s, seats=%s 
            WHERE id=%s
        """, (
            data['title'], data['description'], data['date'], 
            data['location'], data['seats'], data['event_id']
        ))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify(message="✅ Event updated successfully!")
    except Exception as e:
        return jsonify(message=f"Error updating event: {str(e)}"), 500

@app.route('/api/book', methods=['POST'])
def book_event():
    if 'uid' not in session:
        return jsonify(message="Login required"), 403

    data = request.get_json()
    conn = db()
    if not conn:
        return jsonify(message="Database connection failed"), 500

    try:
        cur = conn.cursor(dictionary=True)
        
        # Check if event exists and is approved
        cur.execute("SELECT * FROM events WHERE id=%s AND status='approved'", (data['event_id'],))
        event = cur.fetchone()
        
        if not event:
            return jsonify(message="Event not found or not approved"), 404

        # Check available seats
        cur.execute("SELECT COUNT(*) as booked_count FROM bookings WHERE event_id=%s", (data['event_id'],))
        booked_count = cur.fetchone()['booked_count']
        
        if booked_count >= event['seats']:
            return jsonify(message="Event is fully booked"), 400

        # Create booking with ALL attendee details
        ticket_id = 'TKT' + secrets.token_hex(6).upper()
        
        # Insert with all attendee information
        cur.execute("""
            INSERT INTO bookings(
                user_id, event_id, ticket_id, 
                attendee_name, attendee_email, attendee_phone, attendee_gender
            ) 
            VALUES(%s, %s, %s, %s, %s, %s, %s)
        """, (
            session['uid'], 
            data['event_id'], 
            ticket_id,
            data.get('attendee_name', ''),
            data.get('attendee_email', ''),
            data.get('attendee_phone', ''),
            data.get('attendee_gender', '')
        ))
        
        conn.commit()
        
        return jsonify(message="🎟️ Booking successful!", ticket_id=ticket_id)
        
    except Exception as e:
        print(f"❌ Booking error: {e}")
        return jsonify(message="Booking failed"), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()

@app.route('/api/debug-db')
def debug_db():
    try:
        conn = db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT 1 as test")
            result = cur.fetchone()
            cur.close()
            conn.close()
            return jsonify({"status": "success", "database": "connected", "test": result})
        else:
            return jsonify({"status": "error", "message": "Database connection failed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/debug-events')
def debug_events():
    try:
        conn = db()
        if not conn:
            return jsonify({"status": "error", "message": "No database connection"})
        
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) as event_count FROM events")
        count_result = cur.fetchone()
        
        cur.execute("SELECT * FROM events LIMIT 5")
        events = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "total_events": count_result['event_count'],
            "events": events
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/create-test-events')
def create_test_events():
    try:
        conn = db()
        if not conn:
            return jsonify({"status": "error", "message": "No DB connection"})
        
        cur = conn.cursor()
        
        # Create test events
        test_events = [
            ("Music Festival", "Amazing music festival with top artists", "2025-12-15", "New York", 100),
            ("Tech Conference", "Latest tech trends and innovations", "2025-12-20", "San Francisco", 50),
            ("Food Expo", "Delicious food from around the world", "2025-12-25", "Chicago", 80)
        ]
        
        for title, description, date, location, seats in test_events:
            cur.execute("""
                INSERT INTO events (title, description, date, location, seats, organizer_id, status) 
                VALUES (%s, %s, %s, %s, %s, 1, 'approved')
            """, (title, description, date, location, seats))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Test events created"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/api/admin/bookings-count')
def admin_bookings_count():
    if session.get('role') != 'admin':
        return jsonify(message="Unauthorized"), 403
    
    conn = db()
    if not conn:
        return jsonify({"count": 0})
    
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) as count FROM bookings")
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    return jsonify({"count": result['count']})


@app.route('/api/my-bookings')
def my_bookings():
    if 'uid' not in session:
        return jsonify(message="Login required"), 403

    conn = db()
    if not conn:
        return jsonify([])

    cur = conn.cursor(dictionary=True)
    
    # Updated query with ALL attendee columns including attendee_dob
    cur.execute("""
        SELECT b.*, e.title, e.description, e.date, e.location, 
               b.attendee_name, b.attendee_email, b.attendee_phone, 
               b.attendee_dob, b.attendee_gender
        FROM bookings b
        JOIN events e ON b.event_id = e.id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
    """, (session['uid'],))
        
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(bookings)
# ---------------------- ADMIN ROUTES ----------------------

@app.route('/api/admin/events')
def admin_events():
    if session.get('role') != 'admin':
        return jsonify(message="Unauthorized"), 403

    conn = db()
    if not conn:
        return jsonify([])

    cur = conn.cursor(dictionary=True)
    
    # Try with booking_status first, then fallback
    try:
        cur.execute("""
            SELECT e.*, u.name AS organizer_name,
                   (SELECT COUNT(*) FROM bookings WHERE event_id=e.id AND booking_status='confirmed') AS tickets_booked
            FROM events e
            JOIN users u ON e.organizer_id=u.id
            ORDER BY 
              CASE WHEN e.status = 'pending' THEN 1 ELSE 2 END,
              e.created_at DESC
        """)
    except mysql.connector.Error:
        cur.execute("""
            SELECT e.*, u.name AS organizer_name,
                   (SELECT COUNT(*) FROM bookings WHERE event_id=e.id) AS tickets_booked
            FROM events e
            JOIN users u ON e.organizer_id=u.id
            ORDER BY 
              CASE WHEN e.status = 'pending' THEN 1 ELSE 2 END,
              e.created_at DESC
        """)
        
    events = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(events)

@app.route('/api/admin/update', methods=['POST'])
def admin_update_event():
    if session.get('role') != 'admin':
        return jsonify(message="Unauthorized"), 403

    data = request.get_json()
    conn = db()
    if not conn:
        return jsonify(message="Database connection failed"), 500

    try:
        cur = conn.cursor()
        cur.execute("UPDATE events SET status=%s WHERE id=%s", (data['status'], data['event_id']))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify(message=f"✅ Event {data['status']} successfully!")
    except Exception as e:
        return jsonify(message=f"Error updating event: {str(e)}"), 500
# ---------------------- ADMIN USER MANAGEMENT ROUTES ----------------------

# ---------------------- ADMIN USER / ORGANIZER ROUTES ----------------------

@app.route('/api/admin/users')
def admin_users():
    """Return all users (role = user)"""
    if session.get('role') != 'admin':
        return jsonify(message="Unauthorized"), 403
    conn = db()
    if not conn:
        return jsonify([])
    cur = conn.cursor(dictionary=True)
    # No created_at column, use only existing fields
    cur.execute("SELECT id, name, email, role FROM users WHERE role='user' ORDER BY id DESC")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(users)


@app.route('/api/admin/organizers')
def admin_organizers():
    """Return all organizers (role = organizer)"""
    if session.get('role') != 'admin':
        return jsonify(message="Unauthorized"), 403
    conn = db()
    if not conn:
        return jsonify([])
    cur = conn.cursor(dictionary=True)
    # No created_at column, so fetch only valid columns
    cur.execute("SELECT id, name, email, role FROM users WHERE role='organizer' ORDER BY id DESC")
    organizers = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(organizers)


@app.route('/api/admin/delete-user/<int:user_id>', methods=['DELETE'])
@app.route('/api/admin/delete-organizer/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    """Delete a user or organizer by ID"""
    if session.get('role') != 'admin':
        return jsonify(message="Unauthorized"), 403
    conn = db()
    if not conn:
        return jsonify(message="Database connection failed"), 500
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
        return jsonify(message="✅ Deleted successfully!")
    except Exception as e:
        return jsonify(message=f"Error deleting: {str(e)}"), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/admin/bookings')
def admin_bookings():
    """Return all confirmed bookings with user and event details"""
    if session.get('role') != 'admin':
        return jsonify(message="Unauthorized"), 403
    conn = db()
    if not conn:
        return jsonify([])
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT b.ticket_id, u.name AS user_name, u.email AS user_email,
               e.title AS event_title, e.date AS event_date, b.created_at AS booking_date
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN events e ON b.event_id = e.id
        ORDER BY b.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True, port=5000)