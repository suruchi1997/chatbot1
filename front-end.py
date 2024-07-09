import string

from flask import Flask, request, jsonify, render_template_string
import os
from azure.ai.formrecognizer import FormRecognizerClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
import urllib.request
import json
from docx2pdf import convert
import time
import re


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

combined_text = ""

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<style>
button {color: white; 
        background-color:Green;
        font-style:bold;
        padding: 10px 12px;
        font-size: 12px;
        }
         input[type="text"] {
            width: 300px;
            padding: 10px;
            margin: 5px;
            border: 1px solid #ccc;
            font-size: 16px;
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        body{
            background-color:#cceeff;
            text-align: center;
        }
        textarea {
        width: 400px; /* Adjust width as needed */
        height: 200px; /* Adjust height as needed */
        padding: 10px;
        font-size: 16px;
        border: 1px solid #ccc;
        resize: vertical; /* Allows vertical resizing */
        transition: border-color 0.3s, box-shadow 0.3s;
    }
  

</style>

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title> ChatBot </title>
</head>
<body >
    <h1>ChatBot</h1>
    <br>
    <form id="uploadForm" enctype="multipart/form-data">
        <input type="file" name="file" accept=".pdf,.docx">
        <button type="button" onclick="uploadFile()">Upload File</button><br>
        <textarea id="combinedTextDisplay" readonly></textarea>
    </form>
    <br>
    <div id="queryFormContainer">
        <form class="queryForm">
            
            <input type="text" class="queryInput" name="query" placeholder="Enter Query">
            <button type="button" onclick="submitQuery(this)">Submit</button>
        </form>
    </div>
    <script>
        function uploadFile() {
            var form = document.getElementById('uploadForm');
            var formData = new FormData(form);
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log(data)
                var combinedTextDisplay = document.getElementById('combinedTextDisplay');
                combinedTextDisplay.value = data.combined_text;
                
                var resultDiv = document.createElement('div');
                resultDiv.innerText = data.result;
                document.getElementById('queryFormContainer').appendChild(resultDiv);
            })
            .catch(error => {
                var resultDiv = document.createElement('div');
                resultDiv.innerText = 'Error: ' + error;
                document.getElementById('queryFormContainer').appendChild(resultDiv);
            });
        }
        
        

        function submitQuery(button) {
            const form = button.closest('.queryForm');
            const query = form.querySelector('.queryInput').value;
            fetch('/run-function', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query }),
            })
            .then(response => response.json())
            .then(data => {

                var resultDiv = document.createElement('div');
                resultDiv.innerText = data.result;
                
               
                
                // Insert resultDiv after the current form
                form.insertAdjacentElement('afterend', resultDiv);

                // Append a new query form
                var newForm = document.createElement('form');
                newForm.className = 'queryForm';
                newForm.innerHTML = `
                    <div class="input-wrapper">
                    <input type="text" class="queryInput" name="query", placeholder="Enter Query">
                    <button type="button" onclick="submitQuery(this)">Submit</button>
                    </div>
                `;

                // Insert newForm after the resultDiv
                resultDiv.insertAdjacentElement('afterend', newForm);
            })
            .catch(error => {
                var resultDiv = document.createElement('div');
                resultDiv.innerText = 'Error: ' + error;

                // Insert resultDiv after the current form
                form.insertAdjacentElement('afterend', resultDiv);
            });
        }
    </script>
</body>
</html>


'''
def remove_numbers(input_string):
    return re.sub(r'\d+', '', input_string)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    global combined_text
    if 'file' not in request.files:
        return jsonify(result='No file part')
    file = request.files['file']
    if file.filename == '':
        return jsonify(result='No selected file')
    if file and file.filename.endswith('.pdf'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        try:
            file.save(file_path)
            # store(file)
            combined_text = process_pdf(file_path)
            return jsonify(result='File uploaded and processed successfully',combined_text=combined_text)
        except Exception as e:
            return jsonify(result=f'Error processing file: {str(e)}')
    if file and file.filename.endswith('.docx'):
        try:
            # Convert .docx to .pdf
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            # store(file)
            os.chmod(file_path, 0o755)
            pdf_path = convert_to_pdf(file_path)
            combined_text = process_pdf(pdf_path)

            return jsonify(result='File uploaded, converted, and processed successfully', combined_text=combined_text)
        except Exception as e:
            return jsonify(result=f'Error processing file: {str(e)}')
    return jsonify(result='Invalid file type')


def convert_to_pdf(docx_file):

    pdf_path=os.path.join(app.config['UPLOAD_FOLDER'], "output.pdf")
    result=convert(docx_file, pdf_path)
    print("result",result)
    return pdf_path

@app.route('/run-function', methods=['POST'])
def run_function():
    content = request.json
    query = content['query']
    result = eval(combined_text, query)
    return jsonify(result=result)

def process_pdf(file_path):
    try:
        endpoint = ""
        key = ""
        form_recognizer_client = FormRecognizerClient(endpoint, AzureKeyCredential(key))

        with open(file_path, "rb") as file:
            poller = form_recognizer_client.begin_recognize_content(file)
            result = poller.result()

        combined_text = ""
        for page in result:
            for line in page.lines:
                combined_text += line.text + " "
        combined_text=combined_text.strip()
        translator=str.maketrans("","",string.punctuation)
        combined_text=combined_text.translate(translator)
        return remove_numbers(combined_text)

    except Exception as e:
        return f'Error recognizing content: {str(e)}'

def eval(combined_text, question):
    print("com text",combined_text)
    data = {
        "inputs": {
            "question": question,
            "context": combined_text
        }
    }
    url = ''
    api_key = ''
    if not api_key:
        raise Exception("A key should be provided to invoke the endpoint")

    # headers = {
    #     'Content-Type': 'application/json',
    #     'Authorization': 'Bearer ' + api_key,
    #     'azureml-model-deployment': 'demo'
    # }
    headers= {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key), 'azureml-model-deployment': 'chatbot' }
    body = str.encode(json.dumps(data))
    req = urllib.request.Request(url, body, headers)
    try:
        response = urllib.request.urlopen(req)
        result = response.read().decode('utf-8')
        result_dict = json.loads(result)  # Parse the JSON string into a dictionary
        # print("result", result_dict["answer"])
        return result
    except urllib.error.HTTPError as error:
        print("The request failed with status code: " + str(error.code))
        print(error.info())
        print(error.read().decode("utf8", 'ignore'))
        return str(error)

# def store(file):
#     connection_string=""
#     blob_service_client = BlobServiceClient.from_connection_string(connection_string)
#     container_client = blob_service_client.get_container_client("Mycontainer")
#     container_client.create_container()
#     blob_client = container_client.get_blob_client("myclient")
#     with open(file, "rb") as data:
#         blob_client.upload_blob(data, blob_type="BlockBlob")

if __name__ == '__main__':
     port = int(os.getenv('PORT', 5001))
     app.run(debug=True, host='0.0.0.0', port=port)
    



