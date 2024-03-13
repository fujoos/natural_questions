# Standard library imports
import glob  # Module to find all pathname matching a specified pattern according to the rules used by the Unix shell
import os  # Provides a way of using operating system dependent functionality
import uuid
from functools import lru_cache  # Decorator to cache function calls
from math import ceil  # Used for calculating the ceiling of a division, e.g., for pagination
from os.path import basename, splitext  # Functions for manipulating file paths and names

# Third-party imports
import pandas as pd  # Data manipulation and analysis library
import pyarrow.parquet as pq  # PyArrow's library for direct Parquet file manipulation
from flask import Flask, jsonify, request, render_template  # Flask web framework and its functions
from flask_cors import CORS  # Handling Cross-Origin Resource Sharing (CORS)
from bs4 import BeautifulSoup, Tag  # Import BeautifulSoup

app = Flask(__name__)
CORS(app)

PAGE_SIZE = 10
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the directory where your Parquet files are stored
data_dir = os.path.join(BASE_DIR, 'data')

# Use glob to find all CSV files in the directory
csv_files = glob.glob(os.path.join(data_dir, '*.csv'))

for csv_file in csv_files:
    # Construct the Parquet file path
    base_name = os.path.basename(csv_file)
    parquet_file = os.path.join(data_dir, os.path.splitext(base_name)[0] + '.parquet')

    # Check if the Parquet file already exists
    if not os.path.exists(parquet_file):
        # Read the CSV file
        df = pd.read_csv(csv_file)

        # Write the DataFrame to a Parquet file
        df.to_parquet(parquet_file, engine='pyarrow')

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
        return pd.DataFrame()  # Return an empty DataFrame if the file_id doesn't match

    columns_to_load = ['question', 'long_answers', 'short_answers']

    # Read only the required columns and rows using PyArrow for efficiency
    parquet_table = pq.read_table(filepath, columns=columns_to_load, use_threads=True)
    parquet_df = parquet_table.to_pandas()

    # Calculate end row index for slicing
    end = start + page_size

    # Return only the slice of the DataFrame corresponding to the requested page
    return parquet_df.iloc[start:end]


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

    file_options = {file_id: splitext(basename(file_path))[0] for file_id, file_path in file_mapping.items()}
    return render_template('index.html', run_id=run_id, currentPage=1, totalPages=total_pages,
                           pagination=pagination, file_options=file_options, use_minified_css=use_minified_css,
                           use_minified_js=use_minified_js)


# Function to clean HTML content and fix malformed tables
def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # First, identify structured tables by looking for tables that have 'th' elements
    structured_tables = []
    for table in soup.find_all('table'):
        if table.find('th'):
            structured_tables.append(table)

    # Process each 'tr' element outside structured tables to remove unnecessary 'td' elements
    for tr_element in soup.find_all('tr'):
        # Skip this 'tr' element if it's part of a structured table
        if any(table in structured_tables for table in tr_element.find_parents('table')):
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
    paginated_data_dicts = paginated_data.to_dict(orient='records')

    cleaned_data = [{k: ("" if pd.isnull(v) else v) for k, v in record.items()} for record in paginated_data_dicts]

    cleaned_data_fix = []
    for record in cleaned_data:
        # Clean 'long_answers' and 'short_answers' fields
        for field in ['long_answers', 'short_answers']:
            if record[field]:
                record[field] = clean_html_content(record[field])
        cleaned_data_fix.append(record)

    total_records = get_total_records_for_file(file_id)
    total_pages = ceil(total_records / page_size)

    return jsonify({
        'data': cleaned_data_fix,
        'totalRecords': total_records,
        'pageSize': page_size,
        'totalPages': total_pages,
        'currentPage': page
    })


if __name__ == '__main__':
    app.run(debug=True)
