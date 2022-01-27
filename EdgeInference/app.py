# Importing packages
from flask import Flask, request
from flask_restful import Api, Resource
from database import get_OI_config, get_azure_config
import json
import base64
import io
from PIL import Image

# Getting the OI config file for configurations
oiConfig = get_OI_config()

# Getting the azure credentials from Azure
oiazurecred = get_azure_config()

# Creating the app
app = Flask(__name__)

# Initiating the API
api = Api(app)

# Application configuration
app.config['CORS_HEADERS'] = oiConfig["CORS_HEADERS"]

from app_utils import update_status, check_url
from app_utils import do_inference

class DLModelInference(Resource):
    """
        Class holding the structure and functions needed infer model     
    """ 
     # Constructor of anomaly class
    def __init__(self):
        '''
        Constructor to initialize variables in the anomaly flask service
        '''
        self.unique_id = 'deployed'

        
        # Getting encoded frame from the request
        self.enc_frame = json.loads(request.get_data())['image']
        # Decoding the encoded frame
        self.decode_frame = base64.b64decode(self.enc_frame)
        # Getting the image out of the decoded frame
        self.image = Image.open(io.BytesIO(self.decode_frame))


    def post(self):
        # Initializing the API response
        api_response = {}

        # Calling the inference logic
        api_response = do_inference(self.image)

        # Returning the API output
        return api_response

@app.after_request
def after_request(response):
    '''
    Function to perform action after the request is processed

    Input Parameter:
        response: Flask response variable, passed by the falsk application during runtime.

    Output Parameter:
        response: Flask response variable, passed by the falsk application during runtime

    '''
    # Adding headers after the serving the API request
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Max-Age', '86400')
    return response

# Initializing the app service
api.add_resource(DLModelInference, "/imageinference")

if __name__ == '__main__':
    app.run(host=oiConfig['host'], port=oiConfig['port'])
