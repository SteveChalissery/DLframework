# Importing packages
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from database import get_OI_config, get_azure_config
from azureml.core import Run, Experiment
from azure.core import exceptions
import exception
import requests
from threading import Thread
import os
import json
from azureml.widgets import RunDetails

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
app.config['JSON_SORT_KEYS'] = False

from utlis import update_status, workspace_authentication, initiate_training, clean_azure_resources, status_updater

class TrainingInitiater(Resource):
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
        self.message = 'Trainin Initiated'

        try:
            # Getting the unique_id from the request
            # logger.debug('Getting the unique id from the request')
            self.unique_id = request.get_json()['unique_id']

            # Getting the hyperparameters from the request
            # logger.debug('Getting the failure column from the request')
            self.lr = request.get_json()['lr']
            # logger.debug('Getting the columns to not include in training')
            self.epochs = request.get_json()['epochs']
            self.gpu = request.get_json()['gpu']
            self.models = request.get_json()['models']
            self.batch_size = request.get_json()['batch_size']
            self.augment_options = request.get_json()['augment_options']
            
            

            # Checking if the inputs are provided
            if not self.unique_id:
                raise exception.NullUniqueID
            elif not self.lr:
                raise exception.NullLearningRate
            elif not self.epochs:
                raise exception.NullEpochs
            elif not self.models:
                raise exception.NullModelId
            

            # Updating the Status
            update_status(self.unique_id, status='Starting')

        except (AttributeError, TypeError, KeyError) as error:
            # Logging the error
            # logger.exception(error.__class__)

            # Call the status update function if exception occurs
            update_status(self.unique_id, error)

        except (exception.NullUniqueID, exception.NullEpochs, exception.NullLearningRate, exception.NullModelId, exception.IncorrectOptions) as ex:
            # logger.exception(f'Unique ID cannot be empty')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)

        except Exception as ex:
            # logger.exception(f'[{self.unique_id}] Unknown exception occured. Check logs/status for more details.')
            # Calling the update status function for status API.
            update_status(self.unique_id, ex)
    
    def post(self):
        run_list = []
        GPU_COUNT = 0
        CPU_COUNT = 0
        if(len(self.augment_options)!=0):
            config_options = oiConfig['preprocess']
            print("*************************************")
            print(list(config_options.split(",")))
            print(self.augment_options)
            check = all(item in list(config_options.split(",")) for item in self.augment_options)
            if check is False:
                raise exception.IncorrectOptions
            augmentstr = " ".join(self.augment_options)
        else:
            augmentstr = 'None'
        
        for index, model in enumerate(self.models):
            # Some constants for azure ml training 
            if len(self.gpu) > 1:
                if self.gpu[index]:
                    GPU_COUNT += 1
                else:
                    CPU_COUNT += 1
            else:
                if self.gpu[0]:
                    GPU_COUNT += 1
                else:
                    CPU_COUNT += 1

            # Creating the training configurations
            train_config = {
                "MODEL_DIR" : "AppData/" + str(self.unique_id) + "/" + oiConfig['output_model_dir'] + "/" + model,  # Path to store inference model
                "proj_root" : oiConfig['project_root'], # The root direfctory 
                "TFRECORDS_SUBDIR" : "AppData/" + os.path.join(str(self.unique_id), oiConfig['tfrecord_dir']), # TFRecords and pipeline file directory
                "MODELS_SUBDIR" : oiConfig['Zoo'], # Base Models 
                "SCRIPT_FOLDER" : './scripts', # Scripts to run in AML
                "SCRIPT_FILE" : 'train.py', # Entry script or the trigger script
                "DOCKER_REGR_ADDR" : oiazurecred['docker_registry_address'],
                "DOCKER_REGR_NAME" : oiazurecred['docker_registry_username'],
                "DOCKER_REGR_PASS" : oiazurecred['docker_registry_password'],
                "DOCKER_TRAIN_IMAGE" : oiazurecred['training_docker_image_short_name'],
                "GPU" : int(self.gpu[index] if len(self.gpu) > 1 else self.gpu[0]),
                "BASE_MODEL" : model,
                "EPOCHS": self.epochs[index] if len(self.epochs) > 1 else self.epochs[0],
                "LR": float(self.lr[index] if len(self.lr) > 1 else self.lr[0]),
                "UID": self.unique_id,
                "BATCH_SIZE": self.batch_size[index] if len(self.batch_size) > 1 else self.batch_size[0],
                "GPU_COUNT" : GPU_COUNT,
                "CPU_COUNT" : CPU_COUNT,
                "AUGMENT": augmentstr,
            }

            print(train_config)

            # Getting the AML workspace
            workspace = workspace_authentication(train_config)
            
            # Starting the training 
            run = initiate_training(workspace, train_config)

            run_list.append(run.id)

            # Saving train_config for later use
            if not (os.path.exists(f"{run.id}_config.json".strip())):
                with open(f"{run.id}_config.json".strip(), "w") as data:
                    response_dict = {
                        'train_config' : train_config
                    }
                    data.write(json.dumps(response_dict))
                    data.close()
                    
        # Retuening the api status         
        return jsonify({
                        'status' : str(self.status),
                        'message' : self.message,
                        'RunID' : run_list
                    })

class Status(Resource):

    def __init__(self):
        '''
        Constructor to initialize variables in the anomaly flask service
        '''
        self.run_id = request.get_json()['run_id']
        

    def get(self, unique_id):
        try:
            # Checking if the inputs are provided
            if not self.run_id:
                raise exception.NullRunID
            if not unique_id:
                raise exception.NullUniqueID

        except exception.NullRunID as ex:
            update_status(unique_id, ex)
        except exception.NullUniqueID as ex:
            update_status(unique_id, ex)

        # Getting the status from the training intiator
        try:
            if (os.path.exists(f"{unique_id}_status.json".strip())):
                with open(f"{unique_id}_status.json".strip(), "rb") as status:
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

        # Getting the AML workspace
        workspace = workspace_authentication({'GPU' : 1}, ws_only=True)
        
        # Getting the experiment -
        exp = Experiment(workspace, name=oiazurecred['experiment'])

        # Getting the Run object for the run id
        run = Run(exp, self.run_id)

        # Reading train config
        with open(str(run.id) + '_config.json', 'rb') as data:
            train_config_data = json.loads(data.readlines()[0])
            train_config = train_config_data['train_config']

        # Returning the run status
        status =  run.get_detailed_status()

        # Default status
        api_status = {
                    'Status' : status
                    }
        
        os.makedirs('files', exist_ok=True)
        if os.path.exists('files/70_driver_log.txt'):
            os.remove('files/70_driver_log.txt')

        for f in run.get_file_names():
            if f == "azureml-logs/70_driver_log.txt":

                dest = os.path.join('files', f.split('/')[-1])
                print('Downloading file {} to {}...'.format(f, dest))
                run.download_file(f, dest)

                with open("files/70_driver_log.txt", 'r') as data:
                    logs = data.read()


                logs = logs.split()

                step_list = []
                loss_list = [] 
                api_status = {}
                # print(logs)
                if logs:
                    for index, ch in enumerate(logs):
                        if ch == "step":
                            step_list.append(logs[index+1].strip(":"))
                        if ch == "loss":
                            loss_list.append(logs[index+2])    
                    print(step_list, loss_list)
                    if step_list and loss_list:
                        print("IN")
                        step_list = [float(x) for x in step_list]
                        loss_list = [float(x) for x in loss_list]

                        api_status = {
                            'Status' : status,
                            'percent_done': round((list(set(step_list))[-1])/train_config['EPOCHS'] * 100, 2),
                            'loss' : list(set(loss_list))
                            
                        }
                        
                    else:
                        api_status = {
                            'Status' : status
                        }

                else:
                    api_status = {
                                'Status' : status
                            }
                
        # if status['status'] == "Completed":
            # Cleaning the azure resources
            # clean_azure_resources(run.get_details()['target'], workspace)
        

        return api_status

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
api.add_resource(TrainingInitiater, "/initiateTraining")
api.add_resource(Status, "/getStatus/<string:unique_id>")
app.run(host=oiConfig['host'], port=oiConfig['port'], threaded=True, debug=True)