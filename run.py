#!/usr/bin/env python3
"""
GradList — Graduation Registry Application
Run this file to start the development server.

Usage:
    python run.py

The app will be available at http://localhost:5000
"""
from app import app, init_db

if __name__ == "__main__":
    print("=" * 50)
    print("  🎓 GradList — Graduation Registry Platform")
    print("=" * 50)
    print("  Initializing database...")
    init_db()
    print("  Database ready!")
    print("  Starting server at http://localhost:5000")
    print("  Press Ctrl+C to stop.")
    print("=" * 50)
    app.run(debug=True, port=5000, host="0.0.0.0")
