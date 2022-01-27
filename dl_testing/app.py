# Importing packages
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from database import get_OI_config, get_azure_config
from azure.core import exceptions
import exception
import requests
from threading import Thread
import os
import json
import numpy as np

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
app.config['JSON_SORT_KEYS'] = True

from app_utils import update_status, check_url
from app_utils import do_inference

class DLModelInference(Resource):
    """
        Class holding the structure and functions needed to train the anomaly detection models     
    """ 
    # Constructor of anomaly class
    def __init__(self):
        '''
        Constructor to initialize variables in the anomaly flask service
        '''
        self.unique_id = ''
        self.status = 200
        self.message = 'Testing Initiated'

        try:
            # Getting the unique_id from the request
            # logger.debug('Getting the unique id from the request')
            self.unique_id = request.get_json()['unique_id']

            # Getting the hyperparameters from the request
            # logger.debug('Getting the failure column from the request
            self.models = request.get_json()['model_name']
            self.image_urls = request.get_json()['image_urls']
            # print(len(self.image_urls))
            with open("length.txt", "w") as data:
                data.write(str(len(self.image_urls)))
            # Checking if the inputs are provided
            if not self.unique_id:
                raise exception.NullUniqueID
            elif not self.models:
                raise exception.NullModelName
            elif len(self.image_urls) == 0:
                raise exception.NullImageUrls

            # Updating the Status
            update_status(self.unique_id, status='Starting')

        except (AttributeError, TypeError, KeyError) as error:
            # Logging the error
            # logger.exception(error.__class__)

            # Call the status update function if exception occurs
            update_status(self.unique_id, error)

        except (exception.NullUniqueID, exception.NullModelName, exception.NullImageUrls) as ex:
            # logger.exception(f'Unique ID cannot be empty')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)

        except Exception as ex:
            # logger.exception(f'[{self.unique_id}] Unknown exception occured. Check logs/status for more details.')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)
    
    def post(self):
        # Checking the image url provided are valid
        try:
            for urls in self.image_urls:
                check_url_flag, check_valid_img_flag = check_url(urls)

                if not(check_url_flag):
                    raise exception.InvalidURL
                elif not(check_valid_img_flag):
                    raise exception.InvalidImageURL
            
            
            if os.path.exists(f"{self.unique_id}_testStatus.json"):
                f = open(f"{self.unique_id}_testStatus.json", "a")
                f.truncate(0)
                f.close()
            else:
                with open(f"{self.unique_id}_testStatus.json", "w") as data:
                    pass
            
            #Initializinf the api_response
            api_response = {}
            temp_dict = {}

            # Inferencing
            scores = []
            def worker(value):
                # Starting the testing of image on models 
                for model in self.models:
                    for url in self.image_urls:
                        temp_dict[url] = do_inference(self.unique_id, model, url)
                        print(temp_dict[url])
                        scores.append(temp_dict[url]['score'][0])
                        api_response[model] = temp_dict
   
                        with open(f"{self.unique_id}_testStatus.json", "w") as data:
                            data.write(json.dumps(api_response))
                
                score_list = [item for sublist in scores for item in sublist]
                mean_score = np.mean(score_list)
                api_response['Avg Score'] = mean_score

                with open(f"{self.unique_id}_testStatus.json", "w") as data:
                            data.write(json.dumps(api_response))
                            
            thread = Thread(target=worker, kwargs={'value': request.args.get('value', 5)})
            thread.start()

            # API Response
            return f"Testing Initiated"

        except exception.InvalidURL as ex:
            ex.message = f"Invalid Image URL: {urls}"
            update_status(self.unique_id, ex)

        except exception.InvalidImageURL as ex:
            ex.message = f"URL does not point to a valid image source: {urls}"
            update_status(self.unique_id, ex)

        # Checking if the app has encountered any exception and returning the exception message to the user.
        try:
            if (os.path.exists(f"{self.unique_id}_status.json".strip())):
                with open(f"{self.unique_id}_status.json".strip(), "rb") as status:
                    train_status = json.loads(status.readlines()[0])
                    if train_status['status'] == 'Exception':
                        return train_status
                    status.close()
            else:
                raise FileNotFoundError

        except FileNotFoundError:
            return "Please initiate training"
        except IndexError:
            return "File is empty, check if training is initiated "
        
        return jsonify({
		                 'status' : str(self.status),
						 'message' : self.message
		})


class Status(Resource):

    """
        Class holding the structure and functions needed to check the status of testing done on images     
    """

    def __init__(self):
        '''
        Constructor to initialize variables in the anomaly flask service
        '''

        self.models = request.get_json()['model_name']

    def get(self, unique_id):
        #checking for the valid uniqueID
        try:
            if not unique_id:
                raise exception.NullUniqueID

        except exception.NullUniqueID as ex:
            update_status(unique_id, ex)

        # Opening the json file where training status is written and length.txt file which has number of images provided by user
        try:
            if os.path.exists(f"{unique_id}_testStatus.json"):
                with open(f"{unique_id}_testStatus.json", "r") as data:
                    testStatus = data.readline()
            if os.path.exists("length.txt"):
                with open("length.txt", "r") as length:
                    url_length = length.readline()
            else:
                raise FileNotFoundError
        except:
            return f"Please Initiate Training"
       
        status = {
            'status' : 'started',
            '% Completed': 0
        }
        if testStatus.count('box') == int(url_length):
            testingStatus = json.loads(testStatus)
            return jsonify(testingStatus)
        else:
            status['% Completed'] = (testStatus.count('box')/int(url_length))*100
            return status

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
api.add_resource(DLModelInference, "/getInference")
api.add_resource(Status, "/testStatus/<string:unique_id>")
app.run(host=oiConfig['host'], port=oiConfig['port'], threaded=True, debug=True)