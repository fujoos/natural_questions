# Standard library imports
import glob  # Module to find all pathname matching a specified pattern according to the rules used by the Unix shell
import os  # Provides a way of using operating system dependent functionality
import uuid
from functools import lru_cache  # Decorator to cache function calls
from math import ceil  # Used for calculating the ceiling of a division, e.g., for pagination
from os.path import basename, splitext  # Functions for manipulating file paths and names
# Third-party imports

import pyarrow.parquet as pq  # PyArrow's library for direct Parquet file manipulation
import pyarrow.csv as pa_csv
from flask import Flask, jsonify, request, render_template  # Flask web framework and its functions
from bs4 import BeautifulSoup  # Import BeautifulSoup

import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

import importlib

saved_kaggle_username = os.environ.get('ENCRYPTED_KAGGLE_USERNAME')
saved_kaggle_key = os.environ.get('ENCRYPTED_KAGGLE_KEY')
saved_encryption_key = os.environ.get('ENCRYPTED_KEY')
saved_dataset_path = os.environ.get('KAGGLE_DATASET_PATH')

# Print the retrieved environment variables
print('Retrieved environment variables:')
print(f'ENCRYPTED_KAGGLE_USERNAME: {saved_kaggle_username}')
print(f'ENCRYPTED_KAGGLE_KEY: {saved_kaggle_key}')
print(f'ENCRYPTED_KEY: {saved_encryption_key}')
print(f'KAGGLE_DATASET_PATH: {saved_dataset_path}')


def decrypt_from_base64(encrypted_data, encrypt_key):
    encrypted_data_bytes = base64.b64decode(encrypted_data.encode('utf-8'))  # Decode Base64 string to bytes
    iv = encrypted_data_bytes[:AES.block_size]  # Extract IV
    ciphertext = encrypted_data_bytes[AES.block_size:]  # Extract ciphertext
    cipher = AES.new(encrypt_key, AES.MODE_CBC, iv)  # Initialize cipher
    decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)  # Decrypt and un-pad data
    return decrypted_data.decode('utf-8')  # Return decrypted data as string


# Retrieve the encrypted data from environment variables
encrypted_kaggle_username = os.getenv('ENCRYPTED_KAGGLE_USERNAME')
encrypted_kaggle_key = os.getenv('ENCRYPTED_KAGGLE_KEY')
encrypted_key = os.getenv('ENCRYPTED_KEY')

# Use the same key used for encryption
key = base64.b64decode(encrypted_key.encode('utf-8'))  # Decode Base64-encoded key

# Decrypt the data
decrypted_kaggle_username = decrypt_from_base64(encrypted_kaggle_username, key)
decrypted_kaggle_key = decrypt_from_base64(encrypted_kaggle_key, key)

# Print decrypted data
print("Decrypted Kaggle Username:", decrypted_kaggle_username)
print("Decrypted Kaggle Key:", decrypted_kaggle_key)

# Configure API
os.environ['KAGGLE_USERNAME'] = decrypted_kaggle_username
os.environ['KAGGLE_KEY'] = decrypted_kaggle_key

# Dynamically import the Kaggle API
kaggle_api_module = importlib.import_module('kaggle.api.kaggle_api_extended')
KaggleApi = kaggle_api_module.KaggleApi

api = KaggleApi()
api.authenticate()

# Set the Kaggle dataset path and desired download path
kaggle_dataset_path = os.environ['KAGGLE_DATASET_PATH']
download_path = './data'

# Create the download directory if it doesn't exist
if not os.path.exists(download_path):
    os.makedirs(download_path)

# Check if the csv files already exists in the download directory
if not (os.path.exists(os.path.join(download_path, "Natural-Questions-Base.csv")) and os.path.exists(
        os.path.join(download_path, "Natural-Questions-Filtered.csv"))):
    try:
        # Download dataset files
        api.dataset_download_files(kaggle_dataset_path, path=download_path, unzip=True)
        # api.dataset_download_file(dataset_identifier, file_name, path=download_path, unzip=True)
        print(f'Successfully downloaded and unzipped dataset from {kaggle_dataset_path} to {download_path}')
    except Exception as e:
        print(f'An error occurred while downloading the dataset from Kaggle: {e}')
else:
    print("Dataset zip file already exists in the download directory. Skipping download.")

app = Flask(__name__)

PAGE_SIZE = 10
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the directory where your Parquet files are stored
data_dir = os.path.join(BASE_DIR, 'data')

# Use glob to find all CSV files in the directory
# Convert CSV files to Parquet without using Pandas
for csv_file in glob.glob(os.path.join(data_dir, '*.csv')):
    parquet_file = os.path.join(data_dir, splitext(basename(csv_file))[0] + '.parquet')
    if not os.path.exists(parquet_file):
        # Convert CSV directly to Parquet using PyArrow
        table = pa_csv.read_csv(csv_file)
        pq.write_table(table, parquet_file)
        print(f"Converted {csv_file} to {parquet_file}")
    else:
        print(f"Parquet file already exists for {csv_file}, skipping conversion.")

# Use glob to find all Parquet files in the directory
parquet_files = glob.glob(os.path.join(data_dir, '*.parquet'))

# Create a file mapping dictionary with keys like 'file1', 'file2', etc., and the file paths as values
file_mapping = {f'file{i + 1}': file for i, file in enumerate(parquet_files)}
print('file mappings:', file_mapping)


# Function to load a segment of Parquet data
def load_data_segment(file_id, start, page_size):
    filepath = file_mapping.get(file_id)
    if not filepath:
        return []  # Return an empty DataFrame if the file_id doesn't match

    columns_to_load = ['question', 'long_answers', 'short_answers']

    # Read only the required columns and rows using PyArrow for efficiency
    parquet_table = pq.read_table(filepath, columns=columns_to_load, use_threads=True)

    # Calculate end row index for slicing
    end = start + page_size

    # Slice the PyArrow Table directly
    return parquet_table.slice(start, end - start)


# Cached function to get total records from a file
@lru_cache(maxsize=None)
def get_total_records_for_file(file_id):
    filepath = file_mapping.get(file_id)
    if not filepath:
        return 0

    # Read the Parquet file metadata to get the total number of records without reading the entire file
    try:
        # Open the Parquet file using pyarrow
        parquet_file_read = pq.ParquetFile(filepath)

        # Initialize total_records to 0
        total_records = 0

        # Iterate through each row group in the Parquet file
        for i in range(parquet_file_read.num_row_groups):
            row_group = parquet_file_read.read_row_group(i)
            total_records += row_group.num_rows

        print('Total records', total_records)
        return total_records
    except Exception as e:
        print(f"Failed to read Parquet file {filepath}: {e}")
        return 0


# Home route
@app.route('/')
def home():
    # Path to the minified CSS file
    minified_css = os.path.join(app.static_folder, 'src/style.min.css')
    # Check if the minified CSS file exists
    use_minified_css = os.path.exists(minified_css)

    # Path to the minified JS file
    minified_js = os.path.join(app.static_folder, 'src/script.min.js')

    # Check if the minified JS file exists
    use_minified_js = os.path.exists(minified_js)

    # Generate a unique identifier for this run (or retrieve it from a configuration if it should persist across runs)
    run_id = str(uuid.uuid4())
    file_id = request.args.get('file_id', list(file_mapping.keys())[0])  # Use the first file as default
    total_records = get_total_records_for_file(file_id)
    total_pages = ceil(total_records / PAGE_SIZE)
    pagination = list(range(1, min(6, total_pages + 1)))

    print('run id: ', run_id)
    file_options = {file_id: splitext(basename(file_path))[0] for file_id, file_path in file_mapping.items()}
    return render_template('index.html', run_id=run_id, currentPage=1, totalPages=total_pages,
                           pagination=pagination, file_options=file_options, use_minified_css=use_minified_css,
                           use_minified_js=use_minified_js)


# Function to clean HTML content and fix malformed tables
def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # First, identify structured tables by looking for tables that have 'th' elements
    structured_tables = []
    for table_element in soup.find_all('table'):
        if table_element.find('th'):
            structured_tables.append(table_element)

    # Process each 'tr' element outside structured tables to remove unnecessary 'td' elements
    for tr_element in soup.find_all('tr'):
        # Skip this 'tr' element if it's part of a structured table
        if any(table_element in structured_tables for table_element in tr_element.find_parents('table')):
            continue

        # Remove unnecessary 'td' elements that contain only backticks or whitespace
        for td in tr_element.find_all('td'):
            if td.get_text(strip=True) in {"``", "''", ""}:
                td.decompose()  # Remove the 'td' element

        # Check if 'tr' element is not already inside a 'table'
        if not tr_element.find_parent('table'):
            # Wrap the 'tr' element in a new 'table' element
            new_table = soup.new_tag('table')
            new_table.insert(0, tr_element.extract())  # Extract the 'tr' element and insert it into the 'table'
            soup.append(new_table)  # Append the new 'table' to the soup

    return str(soup)


# Route to serve paginated data from a selected Parquet file
@app.route('/data', methods=['GET'])
def get_data():
    file_id = request.args.get('file_id', list(file_mapping.keys())[0])
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))  # Default to 10 if not provided
    start = (page - 1) * page_size

    paginated_data = load_data_segment(file_id, start, page_size)

    # Convert PyArrow Table to a dictionary of columns
    columns_dict = paginated_data.to_pydict()

    # Transpose to a list of dictionaries (one per row)
    paginated_data_dicts = [dict(zip(columns_dict, t)) for t in zip(*columns_dict.values())]

    # Replace None values with an empty string
    cleaned_data = [{k: ("" if v is None else v) for k, v in record.items()} for record in paginated_data_dicts]

    cleaned_data_fix = []
    for record in cleaned_data:
        # Sentence case 'question' and 'short_answers' fields
        for field in ['question', 'short_answers']:
            if record.get(field):
                record[field] = record[field].capitalize()

    total_records = get_total_records_for_file(file_id)
    total_pages = ceil(total_records / page_size)

    return jsonify({
        'data': cleaned_data,
        'totalRecords': total_records,
        'pageSize': page_size,
        'totalPages': total_pages,
        'currentPage': page
    })


if __name__ == '__main__':
    app.run(debug=True)
