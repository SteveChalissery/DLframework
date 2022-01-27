# Importing packages
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from database import get_OI_config, get_azure_config
import requests


# Getting the OI config file for configurations
oiConfig = get_OI_config()

# Getting the azure credentials from Azure
oiazurecred = get_azure_config()

# Importing utils
import utils

# Creating the app
app = Flask(__name__)

# Initiating the API
api = Api(app)

# Application configuration
app.config['CORS_HEADERS'] = oiConfig["CORS_HEADERS"]
app.config['JSON_SORT_KEYS'] = False

class DLModelInference(Resource):
    """
        Class holding the structure and functions needed to train the anomaly detection models     
    """ 

    def post(self):
        # Checking the image url provided are valid

        try:
            # Getting the unique_id from the request
            self.data = request.get_json()['data']
            print(self.data)

            # Checking if the inputs are provided
            if not self.data:
                return "Data not present in the json body"
        except (AttributeError, TypeError, NameError) as e:
            return str(e)

        try:
            
            # Initializinf the api_response
            api_response = {}

            # Inferencing
            _, _, scoring_uri, access_keys = utils.get_deployement_details()

            # Calling the Scoring API
            headers = {'Content-Type': 'application/json',
                        'Authorization': ('Bearer ' + access_keys[0])}

            print(scoring_uri[0])
            input_data = self.data
            resp = requests.post(scoring_uri[0], input_data, headers=headers)
            if resp.status_code == 200:
                api_response = resp.json()
            else:
                api_response = resp.text

            print(api_response)
            
            # API Response
            return jsonify(api_response)

        except Exception as e:
            return str(e)

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
app.run(host=oiConfig['host'], port=5000, threaded=True, debug=True)