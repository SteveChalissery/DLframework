import json
from flask import Flask, jsonify, request
from flask_cors import CORS

from azure.storage.blob import BlobServiceClient
import azure


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['JSON_SORT_KEYS'] = False


connect_str = 'DefaultEndpointsProtocol=https;AccountName=stdliopplatformdev001;' \
              'AccountKey=Svo4kbk1P5GD4ES0IgWX4olyJq4MA75EEnz+QlPAaBFJOUk0RzblXKCEBgo3q5LeQktjg5Gw5lYP/2rSxiBcSA==;' \
              'EndpointSuffix=core.windows.net'
container_name = 'oidlframework'
account_name = 'stdliopplatformdev001'



blob_service_client = BlobServiceClient.from_connection_string(connect_str)

# Holder of the config file
blob_client = blob_service_client.get_blob_client(container=container_name, blob='Configs/ModelsConfig.json')

# Writing the data in the file to local folder
with open('./'+'ModelsConfig.json', 'wb') as data:
    try:
        # Downloading stream of config data
        download_stream = blob_client.download_blob()
        # Reading the config into a JSON dict
        modelConfig = json.loads(download_stream.readall())
        # Closing the stream
        data.close()
    except azure.core.exceptions.ResourceNotFoundError:
        print("Blob not found with given name")

class ModelSelectionEntry:
    def flask_app(self):
        return jsonify(modelConfig)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Max-Age', '86400')
    return response


@app.route('/getModels', methods=["GET","POST"])
def modelSelection_app():
    modelSelection = ModelSelectionEntry()
    modelSelection = modelSelection.flask_app()
    return modelSelection


app.run(host='0.0.0.0', port=5004, debug=True)