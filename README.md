# README for the Natural Questions (NQ) Dataset and Flask CSV Reader App

## Context
The Natural Questions (NQ) dataset is a comprehensive collection of real user queries submitted to Google Search, with answers sourced from Wikipedia by expert annotators. Created by Google AI Research, this dataset aims to support the development and evaluation of advanced automated question-answering systems. The version provided here includes 89,312 meticulously annotated entries, tailored for ease of access and utility in natural language processing (NLP) and machine learning (ML) research.

## Data Collection
The dataset is composed of authentic search queries from Google Search, reflecting the wide range of information sought by users globally. This approach ensures a realistic and diverse set of questions for NLP applications.

## Data Pre-processing
The NQ dataset underwent significant pre-processing to prepare it for NLP tasks:
- Removal of web-specific elements like URLs, hashtags, user mentions, and special characters using Python's "BeautifulSoup" and "regex" libraries.
- Grammatical error identification and correction using the "LanguageTool" library, an open-source grammar, style, and spell checker.

These steps were taken to clean and simplify the text while retaining the essence of the questions and their answers, divided into 'questions', 'long answers', and 'short answers'.

## Data Storage

The unprocessed data, including answers with embedded HTML, empty or complex long and short answers, is stored in "Natural-Questions-Base.csv". This version retains the raw structure of the data, featuring HTML elements in answers, and varied answer formats such as tables and lists, providing a comprehensive view for those interested in the original dataset's complexity and richness.
The processed data is compiled into a single CSV file named "Natural-Questions-Filtered.csv". The file is structured for easy access and analysis, with each record containing the processed question, a detailed answer, and concise answer snippets.


## Filtered Results
The filtered version is available where specific criteria, such as question length or answer complexity, were applied to refine the data further. This version allows for more focused research and application development.

## Flask CSV Reader App
This repository also includes a Flask-based CSV reader application designed to read and display contents from the "NaturalQuestions.csv" file. The app provides functionalities such as:
- Viewing questions and answers directly in your browser.
- Filtering results based on criteria like question keywords or answer length.

## Acknowledgements
The creation and refinement of the NQ dataset were made possible by the extensive resources and support from the Google AI research community. Their dedication to advancing NLP and question-answering technology is invaluable.

- [Google AI Research - Natural Questions](https://ai.google.com/research/NaturalQuestions)
- [Natural Questions GitHub Repository](https://github.com/google-research-datasets/natural-questions)

## Inspiration
The NQ dataset serves as a pivotal resource for understanding user queries and improving question-answering systems. It contributes to the advancement of AI technologies that better comprehend human questioning patterns and deliver accurate, relevant responses.

## Getting Started
To explore the dataset and use the Flask app:
1. Clone this repository to your local machine.
2. Ensure Python and Flask are installed.
3. Navigate to the app directory and run `flask run` to start the server.
4. Access the web interface at `http://localhost:5000` to interact with the dataset.
5. See the live demo using the csv files converted to slite db at 'https://fujoos.pythonanywhere.com/'
6. For enabling automated CSV downloads and conversion to an SQLite database, rename the file [index (auto csv downloads and convert).py] to index.py and substitute it for the current index.py. Additionally, employ env.py to establish your environment variables 

7. This README provides an overview of the project's context, data processing, and the functionalities of the Flask CSV reader app. For more detailed instructions and documentation, please refer to the specific files and code comments within this repository.