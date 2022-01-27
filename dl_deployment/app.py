# Importing packages
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from database import get_OI_config, get_azure_config
from logutils import logger
import json
import os
import exception
from threading import Thread

import warnings
warnings.filterwarnings('ignore')

# Getting the OI config file for configurations
oiConfig = get_OI_config()

# Getting the azure credentials from Azure
oiazurecred = get_azure_config()

# Getting common application logger
logger = logger(oiConfig)

# Creating the app
app = Flask(__name__)

# Initiating the API
api = Api(app)

# Application configuration
app.config['CORS_HEADERS'] = oiConfig["CORS_HEADERS"]
app.config['JSON_SORT_KEYS'] = False

from utility import update_status, deploy_model, check_valid_input

class DeployInferenceModel(Resource):

    # Initializing the Deployment class
    def __init__(self):
        """
        Class holding the structure and functions needed to deploy the model on cloud.     
        """ 
        # Starting the logging for this service
        logger.info('Model Deployment API Hit')
        logger.info('Logging messages for deployment Service')

        # Initaizing global variables
        self.unique_id, self.model_name = "" , ""


        try:
            # Getting the unique_id from the request
            logger.debug('Getting the unique id from the request')
            self.unique_id = str(request.get_json()['unique_id'])

            # Getting the predictFailure col from the request
            logger.debug('Getting the model name from the request')
            self.model_name = request.get_json()['model_name']

            # Checking if the inputs are provided
            if not self.unique_id:
                raise exception.NullUniqueID
            elif not self.model_name:
                raise exception.NullModelName

            status = check_valid_input(self.unique_id, self.model_name)

            if status == 'Model':
                raise exception.InvalidModelName
            elif status == 'ID':
                raise exception.InvalidUniqueID

        except (AttributeError, TypeError, KeyError) as error:
            # Logging the error
            logger.exception(error.__class__)
            print(f"{str(error.__class__)}")

            # Call the status update function if exception occurs
            update_status(self.unique_id, error)

        except exception.NullUniqueID as ex:
            logger.exception(f'Unique ID cannot be empty')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)

        except exception.NullModelName as ex:
            logger.exception(f'Model name cannot be empty')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)

        except exception.InvalidUniqueID as ex:
            logger.exception(f'Invalid Unique ID provided')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)

        except exception.InvalidModelName as ex:
            logger.exception(f'Invalid model name provided')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)

        except Exception as ex:
            logger.exception(f'[{self.unique_id}] Unknown exception occured. Check logs/status for more details.')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)

    def post(self):

        # Successfull status completion
        if (os.path.exists(f"{self.unique_id}_status.json".strip())):
            with open(f"{self.unique_id}_status.json".strip(), "rb") as status:
                deploy_status = json.loads(status.readlines()[0])
                status.close()

            if deploy_status['status'] == 'Exception':
                return deploy_status

        # Starting a thread for sending the video frames
        thread = Thread(target=deploy_model, kwargs={'unique_id': request.args.get('unique_id', self.unique_id),
                                                    'model_name' : request.args.get('model_name', self.model_name)})
        
        thread.setDaemon(True) 
        thread.start()

        deploy_status = {
            'status' : 'Starting',
            'message' : f'Deployment for model {self.model_name} started for ID {self.unique_id}.'
        }

        return deploy_status


class Status(Resource):
    # Definging the get endpoint for the status API call
    def get(self, unique_id):

        # Default status while the deployment is not yet started
        deployment_status = {
            "status" : "Started",
            "progress": "NA",
            "message": "Deployment is in progress."
        }
        try:
            with open(f"{str(unique_id)}_status.json", "r") as status:
                deployment_status = json.loads(status.readlines()[0])
        except FileNotFoundError:
            return deployment_status
        except IndexError:
            return deployment_status
        return deployment_status

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
api.add_resource(DeployInferenceModel, "/deployModel")
api.add_resource(Status, "/getStatus/<string:unique_id>")
app.run(host=oiConfig['host'], port=oiConfig['port'], threaded=True, debug=True)