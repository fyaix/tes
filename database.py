import sqlite3
import json
import os
from pathlib import Path
import hashlib
import datetime
import secrets

DB_FILE = "vortexvpn.db"

def init_db():
    """Initialize the local database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create test_sessions table for storing test results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_setting(key, value):
    """Save a setting to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (key, str(value)))
    
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    """Get a setting from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        try:
            # Try to parse as JSON first
            return json.loads(result[0])
        except:
            # Return as string if not JSON
            return result[0]
    
    return default

def save_github_config(token, owner, repo):
    """Save GitHub configuration."""
    config = {
        'token': token,
        'owner': owner,
        'repo': repo
    }
    save_setting('github_config', json.dumps(config))

def get_github_config():
    """Get GitHub configuration."""
    config = get_setting('github_config')
    # get_setting already parses JSON, so just return it
    return config

def save_test_session(results_data):
    """Save test session results."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO test_sessions (session_data)
        VALUES (?)
    ''', (json.dumps(results_data),))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return session_id

def get_latest_test_session():
    """Get the latest test session."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT session_data FROM test_sessions 
        ORDER BY created_at DESC LIMIT 1
    ''')
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        try:
            return json.loads(result[0])
        except:
            return None
    return None

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            is_verified INTEGER DEFAULT 0,
            verification_token TEXT,
            reset_token TEXT,
            reset_token_expiry DATETIME,
            github_token TEXT,
            github_owner TEXT,
            github_repo TEXT
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, email):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)', (username, hash_password(password), email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    return user

def verify_user_password(username, password):
    user = get_user_by_username(username)
    if user and user['password_hash'] == hash_password(password):
        return True
    return False

def set_verification_token(username, token):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET verification_token=? WHERE username=?', (token, username))
    conn.commit()
    conn.close()

def verify_user_email(token):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET is_verified=1, verification_token=NULL WHERE verification_token=?', (token,))
    conn.commit()
    conn.close()

def set_reset_token(email, token, expiry):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET reset_token=?, reset_token_expiry=? WHERE email=?', (token, expiry, email))
    conn.commit()
    conn.close()

def verify_reset_token(token):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE reset_token=? AND reset_token_expiry > ?', (token, datetime.datetime.utcnow()))
    user = c.fetchone()
    conn.close()
    return user

def update_user_password(email, new_password):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET password_hash=?, reset_token=NULL, reset_token_expiry=NULL WHERE email=?', (hash_password(new_password), email))
    conn.commit()
    conn.close()

def update_user_profile(username, new_username=None, new_email=None):
    conn = get_db()
    c = conn.cursor()
    if new_username:
        c.execute('UPDATE users SET username=? WHERE username=?', (new_username, username))
    if new_email:
        c.execute('UPDATE users SET email=?, is_verified=0 WHERE username=?', (new_email, username))
    conn.commit()
    conn.close()

def delete_user(username):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username=?', (username,))
    conn.commit()
    conn.close()

def set_github_config_for_user(username, token, owner, repo):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET github_token=?, github_owner=?, github_repo=? WHERE username=?', (token, owner, repo, username))
    conn.commit()
    conn.close()

def get_github_config_for_user(username):
    user = get_user_by_username(username)
    if user:
        return {
            'token': user['github_token'],
            'owner': user['github_owner'],
            'repo': user['github_repo']
        }
    return None

def generate_token():
    return secrets.token_urlsafe(32)

# Initialize database on import
init_db()
create_tables()