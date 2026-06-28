import sqlite3
from flask import Flask, request, render_template_string
import html

app = Flask(__name__)

# Fixed Hardcoded secret
import os
API_KEY = os.environ.get("API_KEY", "default-key-for-dev")

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Fixed SQL Injection
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username=? AND password=?"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return "Welcome!"
    return "Invalid credentials"

@app.route('/search')
def search():
    query = request.args.get('q', '')
    # Fixed XSS
    escaped_query = html.escape(query)
    return render_template_string(f"<h1>Search results for: {escaped_query}</h1>")

if __name__ == '__main__':
    app.run(debug=False)
