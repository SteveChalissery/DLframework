'''
Utility scripts containing functions to deploy model.
'''

# Importing packages
import json
import datetime
from azure.storage.blob import BlobServiceClient
from azureml.core.authentication import ServicePrincipalAuthentication
from azureml.core.model import InferenceConfig
from azureml.core.environment import Environment
from azureml.core.conda_dependencies import CondaDependencies
from azureml.core.compute import ComputeTarget, AksCompute
from azureml.exceptions import ComputeTargetException
from azureml.core.environment import Environment, DEFAULT_GPU_IMAGE
from azureml.core import Workspace
from azureml.core.webservice import AksWebservice, Webservice
from azureml.core.model import Model
import requests
import os
import shutil
import azure
import logging

# Getting the OIConfiguration
with open('OIConfig.json', 'rb') as data:
    oiconfig = json.load(data)

# Getting the azure credentials
with open('OIAzureCred.json', 'rb') as data:
    oiazurecred = json.load(data)

# Logging information
logger = logging.getLogger('DL-Framework')    

# Total steps involved in the deployment process
total_steps = 5
current_completed_steps = 0
uuid = 0
modelName = ""

# Function to deploy the model on AKS
def deploy_model(unique_id, model_name):

    # Global variables 
    global modelName
    global uuid
    global current_completed_steps

    # Assigning global variables values
    modelName = model_name
    uuid = unique_id

    # Cleaning previous deployment services and getting the workspace
    workspace = clean_deployment_services()

    # Uploading deployment information 
    upload_deployment_config()

    # Copy config file to model folder
    shutil.copy('DeployConfig.json', './models')
    logger.debug(f"Updated the deployment config file")

    # Updating the progress
    current_completed_steps = 1
    update_deployment_progress(current_completed_steps, "Updated Deployemnt config")

    # Downloading the deployed model locally
    logger.info('Downloading the deployed model.')
    download_model_local(unique_id, model_name)
    current_completed_steps += 1
    update_deployment_progress(current_completed_steps, "Downloaded deployed model")

    # Getting the workspace from azure ml
    logger.info('Getting azure ml workspace information.')
    current_completed_steps += 1
    update_deployment_progress(current_completed_steps, "Deployment Initializing done")
    logger.debug(f'Workspace Initialized : \nWorkspace Name : {workspace.get_details()["name"]}')

    # Registering the model with azure ml
    logger.info('Registering the model in the workspace')
    model = register_model(workspace, model_name)
    current_completed_steps += 1
    update_deployment_progress(current_completed_steps, "Model Registered")
    logger.debug(f'Model successfully registeres in the workspace {workspace.get_details()["name"]}\n'\
                f'Model Name: {model.name}, Model Version: {model.version}')
    
    # Creating a inference engine
    logger.info('Starting the deployment process')
    response = create_inference_engine(workspace, unique_id, model_name, model)
    current_completed_steps += 1
    update_deployment_progress(current_completed_steps, "Model successfully deployed", response)
    logger.debug(f'Model Successfully deployed.\nModel URI: {response["scoring_uri"]}')

    # Updating the deployment config and uploading on azure
    upload_deployment_config(response, update_and_upload=True)



# Function to clean the previous deployment services
def clean_deployment_services():
    aks_service_name = None
    # Getting the previously aks service name
    logger.debug('Getting the previous deployment configuration')

    aks_service_name = get_deployement_details()
    
    # Getting the workspace
    workspace = get_workspace()

    if aks_service_name:
        # Intializing the model with the aks service
        logger.info("Initalizing the web service of previous deployment")
        try:
            model = Webservice(workspace, aks_service_name)

            # Detleting the previously deployed service
            logger.info("Cleaning the previous deployments.")
            model.delete()
        except:
            pass

    # Returning the workspace information
    return workspace

# Function to get the deployment configuration
def get_deployement_details():

    # Global variable
    global uuid

    # Initializing return variables
    aks_service_name = ""

    # Service client of azure to connect to blob storage
    blob_service_client = BlobServiceClient.from_connection_string(oiazurecred['blobconnectionstring'])

    blob_path = "Configs/DeployConfig.json"

    # Holder of the config file
    blob_client = blob_service_client.get_blob_client(container=oiazurecred['blobcontainername'], 
                                                        blob=blob_path)

    # Writing the data in the file to local folder
    with open('DeployConfig.json', 'wb') as data:
        try:
            # Downloading stream of config data
            download_stream = blob_client.download_blob()
            # Writing it in a config file
            data.write(download_stream.readall())
            # Closing the stream
            data.close()
        except azure.core.exceptions.ResourceNotFoundError as error:
            # Call the status update function if exception occurs
            update_status(uuid, error)


    if (os.path.exists(f"DeployConfig.json")):
        with open('DeployConfig.json', 'rb') as data:
        
            deployData = json.loads(data.readlines()[0])
            try:
                aks_service_name = deployData['aks_service_name']
                print(aks_service_name)
            except Exception as e:
                pass

    return aks_service_name

# Function to upload the deployment config
def upload_deployment_config(response=None, update_and_upload=False):
    global uuid
    global modelName
    if not update_and_upload:
        # Initializing the data variable
        data = {}
        # Model Path
        logger.info("Updating the deployment configuration file containing deployed model information")
        path = f"https://{oiazurecred['blobaccountname']}.blob.core.windows.net/{oiazurecred['blobcontainername']}/AppData/{uuid}/models/{modelName}/model/frozen_inference_graph.pb"
        data['unique_id'] = uuid
        data['Model Name'] = modelName
        data['Model Path'] = path
        data['TimeStamp'] = str(datetime.datetime.now())

        with open('./'+'DeployConfig.json','w') as datafile:
            json.dump(data, datafile)
    else:
        with open('./'+'DeployConfig.json','r') as datafile:
            deploy_config = json.loads(datafile.readlines()[0])
        
        # Updating deployconfiguration with deployment information
        deploy_config['scoring_uri'] = response['scoring_uri']
        deploy_config['API_Keys'] = response['API Keys']
        deploy_config['aks_service_name'] = response['aks_service_name']
        

        with open('./'+'DeployConfig.json','w') as datafile:
            json.dump(deploy_config, datafile)
        

    blob_service_client = BlobServiceClient.from_connection_string(oiazurecred['blobconnectionstring'])
    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(container=oiazurecred['blobcontainername'], blob='Configs/DeployConfig.json')
    with open('./'+'DeployConfig.json','rb') as data:
        blob_client.upload_blob(data, overwrite=True)

# Function to update the deployment progress
def update_deployment_progress(current_completed_steps, message="", response=None):
    # Total steps
    global total_steps
    global uuid

    # Updating the status file
    with open(str(uuid) + "_status.json", 'w') as data:
        percent_complete = (current_completed_steps / total_steps) * 100
        if percent_complete ==100:
            to_write = {
            "status" : "Completed",
            "progress" : str(percent_complete) + "%",
            "messgae" : message,
            "scoring_uri": response["scoring_uri"]
        }
        else:
            to_write = {
                "status" : "Running",
                "progress" : str(percent_complete) + "%",
                "messgae" : message
            }
        data.write(json.dumps(to_write))


# Function to create the inference engine for the deployed model
def create_inference_engine(workspace, unique_id, model_name, model):
    # Create the environment
    myenv = Environment(name="tfod-env")
    conda_dep = CondaDependencies()

    # Define the packages needed by the model and scripts
    # You must list azureml-defaults as a pip dependency
    conda_dep.add_pip_package("azureml-defaults")
    conda_dep.add_pip_package("tensorflow-gpu==1.15")
    conda_dep.add_pip_package("azure-storage-blob==12.3.0")
    conda_dep.add_pip_package("opencv-python")
    conda_dep.add_pip_package("scikit-image")

    # Adds dependencies to PythonSection of myenv
    myenv.python.conda_dependencies = conda_dep
    # Set the container registry information
    myenv.docker.base_image_registry.address = oiazurecred['docker_registry_address']
    myenv.docker.base_image_registry.username = oiazurecred['docker_registry_username']
    myenv.docker.base_image_registry.password = oiazurecred['docker_registry_password']
    myenv.docker.base_image = "tfoddeploy"
    myenv.inferencing_stack_version = 'latest'
    # myenv.docker.enabled = True
    

    # Inference Configuration
    inference_config = InferenceConfig(entry_script="score.py",
                                    source_directory='scoring',
                                    environment=myenv)

    # Deployment configuration
    aks_target = create_aks_config(workspace)
    gpu_aks_config = AksWebservice.deploy_configuration(autoscale_enabled=True,
                                                    cpu_cores=4,
                                                    memory_gb=8)

 
    # Name of the web service that is deployed
    aks_service_name =    "_".join(model_name.split("_")[:-4]).replace('_', '-') + '-' + str(unique_id)

    # Deploy the model
    logger.info("Deploying the model")
    aks_service = Model.deploy(workspace,
                            models=[model],
                            inference_config=inference_config,
                            deployment_config=gpu_aks_config,
                            deployment_target=aks_target,
                            name=aks_service_name)

    aks_service.wait_for_deployment(show_output=True)


    # Final response from the deployment function
    response = {
        "scoring_uri" : aks_service.scoring_uri,
        "API Keys" : aks_service.get_keys(),
        "aks_service_name" : aks_service_name
    }
    return response

def create_aks_config(workspace):
    global current_completed_steps
    
    # Choose a name for your cluster
    aks_name = "aks-gpu"

    # Check to see if the cluster already exists
    try:
        aks_target = AksCompute(workspace=workspace, name=aks_name)
        print('Found existing compute target')
    except ComputeTargetException:
        print('Creating a new compute target...')
        # Provision AKS cluster with GPU machine
        prov_config = AksCompute.provisioning_configuration(vm_size="Standard_NC6S_V3")

        # Create the cluster
        aks_target = AksCompute.create(
            workspace=workspace, name=aks_name, provisioning_configuration=prov_config
        )

        aks_target.wait_for_completion(show_output=True)
        update_deployment_progress(current_completed_steps, )
    return aks_target


# Function to get the workspace from Azure ML
def get_workspace():
    # Getting the azure credentials 
    subscription_id = oiazurecred['subscription_id']
    resource_group = oiazurecred['resource_group']
    workspace_name = oiazurecred['workspace_name']

    # Connecting to the workspace
    service_principal = ServicePrincipalAuthentication(tenant_id="b2b31fd7-64c7-49ba-bb99-9069b9dc0537", # tenantID
                                    service_principal_id="dbafd8e5-5b1d-412f-9d39-ff1e4738d7cb", # clientId
                                    service_principal_password="Y62uDg91oTcaaEy-b~On_N_CG0ugea3D8~") # clientSecret

    workspace = Workspace(subscription_id=subscription_id,
                resource_group=resource_group,
                workspace_name=workspace_name,
                auth=service_principal)
 
    return workspace

# Function to register the model on Azure ML
def register_model(workspace, model_name):
    # Registering the model
    model = Model.register(model_path = "./models",
                       model_name = "tfod_"+ "_".join(model_name.split("_")[:-5]),
                       description = "TFOD Object detection model.",
                       workspace = workspace)

    return model


# Function to download the model locally
def download_model_local(unique_id, model_name):
     # Service client of azure to connect to blob storage
    blob_service_client = BlobServiceClient.from_connection_string(oiazurecred['blobconnectionstring'])

    blob_path = "/AppData/" + str(unique_id) + "/models/" + model_name + "/model/frozen_inference_graph.pb"

    # Holder of the config file
    blob_client = blob_service_client.get_blob_client(container=oiazurecred['blobcontainername'], 
                                                        blob=blob_path)

    if not os.path.exists("models/" + "_".join(model_name.split("_")[:-5])):
        os.makedirs("models/" + "_".join(model_name.split("_")[:-5]))

    # Writing the data in the file to local folder
    with open('models/'+ "_".join(model_name.split("_")[:-5]) + '/frozen_inference_graph.pb', 'wb') as data:
        try:
            # Downloading stream of config data
            download_stream = blob_client.download_blob()
            # Writing it in a config file
            data.write(download_stream.readall())
            # Closing the stream
            data.close()
        except azure.core.exceptions.ResourceNotFoundError as error:
            print("Blob not found with given name")
            # Call the status update function if exception occurs
            update_status(unique_id, error)

    # Downloading the labelmap
    blob_path = "/AppData/" + str(unique_id) + "/annotations/tfrecord/label_map.pbtxt"

    # Holder of the config file
    blob_client = blob_service_client.get_blob_client(container=oiazurecred['blobcontainername'], 
                                                        blob=blob_path)

    # Writing the data in the file to local folder
    with open('models/'+  "_".join(model_name.split("_")[:-5])  + '/label_map.pbtxt', 'wb') as data:
        try:
            # Downloading stream of config data
            download_stream = blob_client.download_blob()
            # Writing it in a config file
            data.write(download_stream.readall())
            # Closing the stream
            data.close()
        except azure.core.exceptions.ResourceNotFoundError as error:
            print("Blob not found with given name")
            # Call the status update function if exception occurs
            update_status(unique_id, error)

def check_valid_input(unique_id, model_name):
    # Checking if the url is valid and points to an image source.
    url = f"https://{oiazurecred['blobaccountname']}.blob.core.windows.net/{oiazurecred['blobcontainername']}/AppData/{unique_id}"
    url_status = requests.get(url)
    status = 'Success'
    if url_status.status_code == 200:
        print(model_name)
        url = f"https://{oiazurecred['blobaccountname']}.blob.core.windows.net/{oiazurecred['blobcontainername']}/AppData/{unique_id}/models/{model_name}"
        url_status = requests.get(url)
        if url_status.status_code == 200:
            pass
        else:
            status = 'Model' 
    else:
        status = 'ID'
    
    return status

def update_status(unique_id, exception_obj=None, status='Exception'):
    '''
    Function to update the status file when an exception occurs.
    Parameters:
        Input:
            unique_id : Unique Id to find the status file.
            exception_obj : Exception obj
            status : Writing reason for the update
        Output:
            None : Returns nothing
    '''
    if status == 'Exception':
        with open(unique_id + '_status.json', 'w') as data:
            # Creating response dict
            response_dict = {
                'status' : status,
                'response' : {
                    'Class' : str(exception_obj.__class__),
                    'Message' : str(exception_obj)
                }
            }
            data.write(json.dumps(response_dict))
            data.close()
    
    if status == 'Started':
        with open(unique_id + '_status.json', 'w') as data:
            # Creating response dict
            response_dict = {
                'status' : status,
                'response' : {}
            }
            data.write(json.dumps(response_dict))
            data.close()

    if status == 'Starting':
        with open(unique_id + '_status.json', 'w') as data:
            # Creating response dict
            response_dict = {
                'status' : status,
                'response' : {}
            }
            data.write(json.dumps(response_dict))
            data.close()
