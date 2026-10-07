import os
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
import win32print
from dotenv import load_dotenv

SOFFICE_PATH = "C:/_tools/LibreOffice/program/soffice.exe"

load_dotenv()

# Setăm template_folder la directorul curent pentru a putea servi index.html
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SUMATRA_PATH = os.path.join(CURRENT_DIR, "SumatraPDF-3.6.1-64", "SumatraPDF-3.6.1-64.exe")
app = Flask(__name__, template_folder=CURRENT_DIR, static_folder=CURRENT_DIR)
CORS(app)

# Parola predefinită (poate fi setată în .env ca AUTH_PASSWORD="parola_ta" sau schimbată direct aici)
SECRET_PASSWORD = os.getenv("AUTH_PASSWORD")

# Setup upload and temp directories
UPLOAD_FOLDER = '_uploads'
TEMP_FOLDER = os.path.join(UPLOAD_FOLDER, 'temp')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



def check_printer_status(printer_name):
    try:
        handle = win32print.OpenPrinter(printer_name)
        attributes = win32print.GetPrinter(handle)[13]
        win32print.ClosePrinter(handle)
        return not (attributes & 0x00000400) >> 10  # PRINTER_STATUS_OFFLINE
    except Exception:
        return None


def convert_image_to_pdf(file_path):
    image = Image.open(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    pdf_path = os.path.join(TEMP_FOLDER, f"{base_name}.pdf")

    counter = 1
    while os.path.exists(pdf_path):
        pdf_path = os.path.join(TEMP_FOLDER, f"{base_name}_{counter}.pdf")
        counter += 1

    image.save(pdf_path, "PDF")
    return pdf_path


def convert_office_to_pdf(file_path):
    try:
        subprocess.run([
            SOFFICE_PATH, "--headless", "--convert-to", "pdf:writer_pdf_Export",
            file_path, "--outdir", TEMP_FOLDER
        ], check=True)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        pdf_path = os.path.join(TEMP_FOLDER, f"{base_name}.pdf")
        if os.path.exists(pdf_path):
            return pdf_path
    except subprocess.CalledProcessError as e:
        print(f"LibreOffice conversion error: {e}")
    return None


def send_pdf_to_printer(file_path):
    try:
        subprocess.run([
            SUMATRA_PATH, "-print-to-default", "-silent", file_path
        ], check=True)
        return True
    except Exception as e:
        print(f"Error printing PDF silently: {e}")
        return False


@app.route('/', methods=['GET'])
def serve_index():
    return send_from_directory(CURRENT_DIR, 'index.html')


@app.route('/', methods=['POST'])
def upload_file():
    # Verificare parolă (din header-ul 'X-Password' sau din câmpul 'password' al formularului)
    user_password = request.headers.get('X-Password') or request.form.get('password')

    if not user_password or user_password != SECRET_PASSWORD:
        return jsonify({"error": "Parolă incorectă sau lipsă!"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if '.' not in file.filename or file.filename.rsplit('.', 1)[1] == '':
        return jsonify({"error": "The uploaded file does not have an extension"}), 400

    filename = file.filename
    ext = filename.rsplit('.', 1)[1].lower()
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    printer_name = win32print.GetDefaultPrinter()
    print(printer_name)
    if not check_printer_status(printer_name):
        return jsonify({"error": "Cel mai probabil printerul este stins"}), 503

    # Convert to PDF if needed
    pdf_path = None
    if ext in ['doc', 'docx', 'xlsx', 'xls']:
        pdf_path = convert_office_to_pdf(file_path)
    elif ext in ['png', 'jpg', 'jpeg', 'bmp', 'gif']:
        pdf_path = convert_image_to_pdf(file_path)
    elif ext == 'pdf':
        pdf_path = file_path

    # Send to printer
    if pdf_path and send_pdf_to_printer(pdf_path):
        return jsonify({"message": f"{filename} uploaded and printed"}), 200
    else:
        return jsonify({"error": f"{filename} upload succeeded but printing failed"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)