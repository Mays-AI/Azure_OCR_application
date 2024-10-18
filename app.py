# app.py
import os
import json
import sqlite3
from flask import Flask, render_template, request, redirect, jsonify
from werkzeug.utils import secure_filename
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from datetime import date


# Azure Recognizer credentials 
AZURE_FORM_RECOGNIZER_ENDPOINT = "https://ENDPOINT.azure.com/"
AZURE_FORM_RECOGNIZER_KEY = "_KEY"


app = Flask(__name__) 

#------------------ Database connection function-------------------------------------
def get_db_connection():
    conn = sqlite3.connect('passport_data.db')
    conn.row_factory = sqlite3.Row  # Allows access to columns by name
    return conn

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'} # Allowed file extensions for uploads 
#function to check if the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------------------------- analyze_passport function------------------------------

#Azure Document Analysis Client initialization
def analyze_passport(file_path):
    # Create the DocumentAnalysisClient
    client = DocumentAnalysisClient(
        endpoint=AZURE_FORM_RECOGNIZER_ENDPOINT,
        credential=AzureKeyCredential(AZURE_FORM_RECOGNIZER_KEY)
    )
    
    # Open the file
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document(
            model_id="prebuilt-idDocument",  # Use the prebuilt ID model
            document=f
        )
       
        result = poller.result()  # Get the results
    
    # Extract metadata 
    metadata = {}
    for doc in result.documents:
        metadata["FirstName"] = doc.fields.get("FirstName").value if "FirstName" in doc.fields else "N/A"
        metadata["LastName"] = doc.fields.get("LastName").value if "LastName" in doc.fields else "N/A"
        metadata["PassportNumber"] = doc.fields.get("DocumentNumber").value if "DocumentNumber" in doc.fields else "N/A"
        metadata["Nationality"] = doc.fields.get("Nationality").value if "Nationality" in doc.fields else "N/A"
        metadata["DateOfBirth"] = doc.fields.get("DateOfBirth").value if "DateOfBirth" in doc.fields else "N/A"
        metadata["DateOfIssue"] = doc.fields.get("DateOfIssue").value if "DateOfIssue" in doc.fields else "N/A"
        metadata["DateOfExpiration"] = doc.fields.get("DateOfExpiration").value if "DateOfExpiration" in doc.fields else "N/A"
        metadata["Sex"] = doc.fields.get("Sex").value if "Sex" in doc.fields else "N/A"

    return metadata

#-----------------------------Function to convert date objects to strings-----------------------------------
def convert_dates_to_strings(data):
    if isinstance(data, dict):
        return {k: convert_dates_to_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_dates_to_strings(i) for i in data]
    elif isinstance(data, date):  # Check if the object is a date
        return data.isoformat()  # Convert to string format
    return data

# Home route to render the upload form
@app.route('/')
def upload_form():
    return render_template('upload.html')

#--------------------------- Route to handle file upload and analysis-----------------------
@app.route('/upload', methods=['POST'])
# Modified /upload route to pass metadata to the template for rendering
@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the request has a file
    if 'passport' not in request.files:
        return redirect(request.url)

    file = request.files['passport']

    if file and allowed_file(file.filename):  # Check if the file is allowed and has a filename
        # Save the uploaded file to the uploads folder
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Analyze the uploaded passport using Azure Form Recognizer
        metadata = analyze_passport(file_path)

        # Convert date objects to strings in the metadata
        metadata = convert_dates_to_strings(metadata)

        # Save metadata to the database and file
        save_metadata_as_json(metadata, filename)

        # Check if data was successfully inserted into the database
        success = insert_metadata_into_db(metadata)
        if success:
            print("Data successfully inserted into the database.")
        else:
            print("Failed to insert data into the database.")
        
        # Render the upload form with the metadata passed to the template
        return render_template('upload.html', metadata=metadata)

    return redirect(request.url)

#--------------------Save the extracted metadata as JSON----------------------------
def save_metadata_as_json(metadata, file_name):
    json_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_name}.json")
    with open(json_file_path, 'w') as json_file:
        json.dump(metadata, json_file)
    return json_file_path
 #------------------------------------------ Insert the metadata into the database function -------------------------
def insert_metadata_into_db(metadata):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if the passport number already exists
        cursor.execute('SELECT * FROM passports WHERE PassportNumber = ?', (metadata["PassportNumber"],))
        if cursor.fetchone() is not None:
            print("Duplicate entry found for passport number:", metadata["PassportNumber"])
            return False  # Duplicate entry
        
        # Insert the metadata into the passports table
        cursor.execute('''
            INSERT INTO passports (FirstName, LastName, PassportNumber, Nationality, DateOfBirth, DateOfIssue, DateOfExpiration, Sex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata["FirstName"], metadata["LastName"], metadata["PassportNumber"], metadata["Nationality"], 
            metadata["DateOfBirth"], metadata["DateOfIssue"], metadata["DateOfExpiration"], metadata["Sex"]
        ))
        conn.commit()
        return True  # Successful insertion
    except Exception as e:
        print(f"Error inserting data: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    # Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
