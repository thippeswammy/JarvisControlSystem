"""
conftest.py — adds project root to sys.path so 'jarvis' package is importable.
"""
import sys
import os

# Ensure the project root (JarvisControlSystem/) is on sys.path
sys.path.insert(0, os.path.dirname(__file__))
