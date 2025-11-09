# Online Event Booking & Management (Beginner-friendly)

## Overview
A minimal Flask + MySQL project scaffold for an Event Booking system. Includes user registration/login, event listing, booking with ticket generation, organizer event creation, and an admin dashboard.

## Tech stack
- Frontend: HTML, CSS, JS (templates)
- Backend: Python Flask
- Database: MySQL

## Quick setup (beginner-friendly)
1. Install Python 3.8+ and MySQL.
2. Create a MySQL database named `event_booking_db` and run `models.sql` (provided) to create tables.
3. Edit `app.py` DB_CONFIG with your MySQL credentials.
4. Create and activate a virtualenv:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
5. Run the app:
   ```bash
   python app.py
   ```
6. Open http://127.0.0.1:5000 in your browser.

## Notes for presentation
- Passwords are stored as plain text in this scaffold for simplicity. **Always** hash passwords (bcrypt) in real projects.
- Email sending is not configured; you can add SMTP later.
- This scaffold uses simple SQL helpers — it's intentionally straightforward for beginners.
