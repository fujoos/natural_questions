# Standard library imports
import base64
import csv
import glob  # Module to find all pathname matching a specified pattern according to the rules used by the Unix shell
import importlib
import os  # Provides a way of using operating system dependent functionality
import sqlite3
import uuid
from functools import lru_cache  # Decorator to cache function calls
from math import ceil  # Used for calculating the ceiling of a division, e.g., for pagination

# Third-party imports
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from flask import Flask, jsonify, request, render_template  # Flask web framework and its functions

# Global variable initialization
saved_kaggle_username = None
saved_kaggle_key = None
saved_encryption_key = None
saved_dataset_path = None

# Constants
PAGE_SIZE = 10
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'data.db')
app = Flask(__name__)


def initialize_environment_variables():
    global saved_kaggle_username, saved_kaggle_key, saved_encryption_key, saved_dataset_path
    saved_kaggle_username = os.environ.get('ENCRYPTED_KAGGLE_USERNAME')
    saved_kaggle_key = os.environ.get('ENCRYPTED_KAGGLE_KEY')
    saved_encryption_key = os.environ.get('ENCRYPTED_KEY')
    saved_dataset_path = os.environ.get('KAGGLE_DATASET_PATH')
    # print('Retrieved environment variables:')
    # print(f'ENCRYPTED_KAGGLE_USERNAME: {saved_kaggle_username}')
    # print(f'ENCRYPTED_KAGGLE_KEY: {saved_kaggle_key}')
    # print(f'ENCRYPTED_KEY: {saved_encryption_key}')
    # print(f'KAGGLE_DATASET_PATH: {saved_dataset_path}')


def decrypt_from_base64(encrypted_data, encrypt_key):
    encrypted_data_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
    iv = encrypted_data_bytes[:AES.block_size]
    ciphertext = encrypted_data_bytes[AES.block_size:]
    cipher = AES.new(encrypt_key, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return decrypted_data.decode('utf-8')


def configure_kaggle_api():
    decrypted_kaggle_username = decrypt_from_base64(os.getenv('ENCRYPTED_KAGGLE_USERNAME'), key)
    decrypted_kaggle_key = decrypt_from_base64(os.getenv('ENCRYPTED_KAGGLE_KEY'), key)
    os.environ['KAGGLE_USERNAME'] = decrypted_kaggle_username
    os.environ['KAGGLE_KEY'] = decrypted_kaggle_key
    # print("Decrypted Kaggle Username:", decrypted_kaggle_username)
    # print("Decrypted Kaggle Key:", decrypted_kaggle_key)


def download_kaggle_dataset():
    kaggle_api_module = importlib.import_module('kaggle.api.kaggle_api_extended')
    KaggleApi = kaggle_api_module.KaggleApi
    api = KaggleApi()
    api.authenticate()

    download_path = './data'
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    kaggle_dataset_path = os.environ['KAGGLE_DATASET_PATH']
    if not (os.path.exists(os.path.join(download_path, "Natural-Questions-Base.csv")) and
            os.path.exists(os.path.join(download_path, "Natural-Questions-Filtered.csv"))):
        try:
            api.dataset_download_files(kaggle_dataset_path, path=download_path, unzip=True)
            print(f'Successfully downloaded and unzipped dataset from {kaggle_dataset_path} to {download_path}')
        except Exception as e:
            print(f'An error occurred while downloading the dataset from Kaggle: {e}')
    else:
        print("Dataset files already exist in the download directory. Skipping download.")


def setup_database(csv_files):
    vacuum_needed = False
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Create the metadata table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS db_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )''')

            # Check if the data has already been inserted
            cursor.execute("SELECT value FROM db_meta WHERE key = 'data_inserted'")
            result = cursor.fetchone()

            if result and result[0] == 'true':
                print("Database already set up and data inserted.")
            else:
                vacuum_needed = True
                # Proceed with creating tables based on CSV files and inserting data
                for csv_file in csv_files:
                    table_name = os.path.splitext(os.path.basename(csv_file))[0].replace('-', '_')
                    cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS "{table_name}" (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT,
                        long_answers TEXT,
                        short_answers TEXT
                    )''')

                # Mark data as inserted in the metadata table
                cursor.execute("INSERT INTO db_meta (key, value) VALUES ('data_inserted', 'true')")
                conn.commit()

        # If vacuum_needed, perform VACUUM outside the transaction
        if vacuum_needed:
            print("Performing VACUUM...")
            with sqlite3.connect(DB_PATH) as conn_vacuum:
                conn_vacuum.execute("VACUUM")
                print("VACUUM completed.")

            # After VACUUM, mark it as done in the metadata table
            with sqlite3.connect(DB_PATH) as conn_meta:
                cursor_meta = conn_meta.cursor()
                cursor_meta.execute("INSERT OR REPLACE INTO db_meta (key, value) VALUES ('vacuum_done', 'true')")
                conn_meta.commit()

    except sqlite3.Error as err:
        print(f"An error occurred while setting up the SQLite database: {err}")

    finally:
        print("SQLite database connection is closed.")

def import_csv_to_sqlite(csv_file_path):
    # Increase the maximum field size limit
    csv.field_size_limit(10 ** 6)

    # Derive table name from CSV filename
    table_name = os.path.splitext(os.path.basename(csv_file_path))[0].replace('-', '_')

    with sqlite3.connect(DB_PATH) as conn, open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        cursor = conn.cursor()

        # Check if the table already contains records
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        count = cursor.fetchone()[0]

        # Proceed with insertion only if the table is empty
        if count == 0:
            reader = csv.DictReader(csvfile)
            rows = [(row['question'], row['long_answers'], row['short_answers']) for row in reader]

            insert_query = f'INSERT INTO "{table_name}" (question, long_answers, short_answers) VALUES (?, ?, ?)'
            cursor.executemany(insert_query, rows)  # Use executemany for batch insert
            conn.commit()
        else:
            print(f"No data inserted: The table '{table_name}' already contains records.")




def initialize_app(data_dir):
    # Find all CSV files in the directory
    csv_files = glob.glob(os.path.join(data_dir, '*.csv'))

    # Setup database and tables based on the CSV files
    setup_database(csv_files)

    # Import data from each CSV file into the corresponding table
    for csv_file in csv_files:
        import_csv_to_sqlite(csv_file)


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
    key = base64.b64decode(os.getenv('ENCRYPTED_KEY').encode('utf-8'))
    initialize_environment_variables()
    configure_kaggle_api()
    download_kaggle_dataset()
    # Setup database and other initialization tasks
    initialize_app(DATA_DIR)
    app.run(debug=False)
