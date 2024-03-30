# Standard library imports
import os  # Provides a way of using operating system dependent functionality
import sqlite3
import uuid
from functools import lru_cache  # Decorator to cache function calls
from math import ceil  # Used for calculating the ceiling of a division, e.g., for pagination

# Third-party imports
from flask import Flask, jsonify, request, render_template  # Flask web framework and its functions

# Constants
PAGE_SIZE = 10
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'data.db')
app = Flask(__name__)


# Cached function to get total records from a file
@lru_cache(maxsize=None)
def get_total_records_for_table(table_name):
    """Get the total number of records for a given table in the SQLite database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_records = cursor.fetchone()[0]
            return total_records
    except sqlite3.Error as err:
        print(f"Failed to query SQLite database: {err}")
        return 0


def get_table_names():
    """Retrieve the list of table names from the SQLite database that start with 'natural'."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        # Filter tables to include only those with names starting with 'natural' (case-insensitive)
        return [table[0] for table in tables if table[0].lower().startswith('natural')]


# Home route
@app.route('/')
def home():
    # Path to the minified CSS file
    minified_css = os.path.join(app.static_folder, 'src/style.min.css')
    use_minified_css = os.path.exists(minified_css)  # Check if the minified CSS file exists

    # Path to the minified JS file
    minified_js = os.path.join(app.static_folder, 'src/script.min.js')
    use_minified_js = os.path.exists(minified_js)  # Check if the minified JS file exists

    # Generate a unique identifier for this run
    run_id = str(uuid.uuid4())

    # Get the table names (corresponding to the original CSV files) from the database
    table_names = get_table_names()

    # If 'table_id' is provided in the request, use it; otherwise, default to the first table
    table_id = request.args.get('table_id', table_names[0] if table_names else '')

    # Get the total number of records for the selected table
    total_records = get_total_records_for_table(table_id)
    total_pages = ceil(total_records / PAGE_SIZE)
    pagination = list(range(1, min(6, total_pages + 1)))

    return render_template('index.html', run_id=run_id, currentPage=1, totalPages=total_pages,
                           pagination=pagination, table_options=table_names, selected_table=table_id,
                           use_minified_css=use_minified_css, use_minified_js=use_minified_js)


def load_data_segment(table_name, start, page_size):
    """Retrieve a segment of data from the specified table for pagination."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
        SELECT question, long_answers, short_answers FROM {table_name} 
        LIMIT ? OFFSET ?
        ''', (page_size, start))
        rows = cursor.fetchall()

    # Convert rows to a list of dictionaries for JSON response
    data_dicts = [dict(zip(['question', 'long_answers', 'short_answers'], row)) for row in rows]
    return data_dicts


# Route to serve paginated data from a sqlite table
@app.route('/data', methods=['GET'])
def get_data():
    # Retrieve the table name from request parameters; default to the first table if not specified
    table_name = request.args.get('table_name', get_table_names()[0])
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', PAGE_SIZE))
    start = (page - 1) * page_size

    # Load paginated data from the specified table
    paginated_data = load_data_segment(table_name, start, page_size)

    for record in paginated_data:
        # Sentence case 'question' and 'short_answers' fields
        for field in ['question', 'short_answers']:
            if record.get(field):
                record[field] = record[field].capitalize()

    # Calculate total records and pages for pagination
    total_records = get_total_records_for_table(table_name)
    total_pages = ceil(total_records / page_size)

    return jsonify({
        'data': paginated_data,
        'totalRecords': total_records,
        'pageSize': page_size,
        'totalPages': total_pages,
        'currentPage': page
    })


if __name__ == '__main__':
    app.run(debug=False)
