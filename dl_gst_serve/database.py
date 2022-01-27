# Importing packages
from azure.storage.blob import BlobServiceClient
import azure
import json
import logging
import yaml
import os

logger = logging.getLogger(__name__)
logger.setLevel( logging.DEBUG )
logging.basicConfig(format='IOP DL Logs: %(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Blob related information
connect_str = 'DefaultEndpointsProtocol=https;AccountName=stdliopplatformdev001;' \
              'AccountKey=Svo4kbk1P5GD4ES0IgWX4olyJq4MA75EEnz+QlPAaBFJOUk0RzblXKCEBgo3q5LeQktjg5Gw5lYP/2rSxiBcSA==;' \
              'EndpointSuffix=core.windows.net'
container_name = 'oidlframework'
account_name = 'stdliopplatformdev001'

# Function to get OI configurations
def get_OI_config(download=True):
    '''
    This function will retrieve the OI config file stored in the Azure blob container
    Parameters:
        Input:
            None : Take no input arguments
        Output:
            config : OI config in JSON format.
    '''
    # Initializing config
    config = None

    if download:
        logger.info("Downloading OI Config")
        # Service client of azure to connect to blob storage
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)

        # Holder of the config file
        blob_client = blob_service_client.get_blob_client(container=container_name, blob='Configs/OIConfig.json')

        # Writing the data in the file to local folder
        with open('./'+'OIConfig.json', 'wb') as data:
            try:
                # Downloading stream of config data
                download_stream = blob_client.download_blob()
                # Writing it in a config file
                data.write(download_stream.readall())
                # Reading the config into a JSON dict
                config = json.loads(download_stream.readall())
                # Closing the stream
                data.close()
            except azure.core.exceptions.ResourceNotFoundError:
                print("Blob not found with given name")
    
    else:
        with open('OIConfig.json', 'rb') as data:
            config = json.load(data)

    return config

# Function to get OI configurations
def get_azure_config(download=True):
    '''
    This function will retrieve the OI config file stored in the Azure blob container
    Parameters:
        Input:
            None : Take no input arguments
        Output:
            config : OI config in JSON format.
    '''
    # Initializing config
    config = None

    if download:
        logger.info("Downloading Azure Config")
        # Service client of azure to connect to blob storage
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)

        # Holder of the config file
        blob_client = blob_service_client.get_blob_client(container=container_name, blob='Configs/OIAzureCred.json')

        # Writing the data in the file to local folder
        with open('./'+'OIAzureCred.json', 'wb') as data:
            try:
                # Downloading stream of config data
                download_stream = blob_client.download_blob()
                # Writing it in a config file
                data.write(download_stream.readall())
                # Reading the config into a JSON dict
                config = json.loads(download_stream.readall())
                # Closing the stream
                data.close()
            except azure.core.exceptions.ResourceNotFoundError:
                print("Blob not found with given name")
    else:
        with open('OIAzureCred.json', 'rb') as data:
            config = json.load(data)

    return config

# Function to get the ports_info.yml file
def get_ports_info(download=True):
    '''
    This function will retrieve the OI config file stored in the Azure blob container
    Parameters:
        Input:
            download : Flag to download from azure
        Output:
            ports_info : Ports Information from azure blob storage.
    '''
    # Initializing ports_info
    ports_info = None
    if download:
        logger.info("Downloading Ports Information")
        # Service client of azure to connect to blob storage
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)

        # Holder of the config file
        blob_client = blob_service_client.get_blob_client(container=container_name, blob='Configs/ports_info.yml')

        # Writing the data in the file to local folder
        with open('./'+'ports_info.yml', 'wb') as data:
            try:
                # Downloading stream of config data
                download_stream = blob_client.download_blob()
                # Writing it in a config file
                data.write(download_stream.readall())
                # Reading the config into a JSON dict
                ports_info = yaml.load(download_stream.readall(), Loader=yaml.FullLoader)
                # Closing the stream
                data.close()
            except azure.core.exceptions.ResourceNotFoundError:
                print("Blob not found with given name")
    else:
        with open('ports_info.yml', 'rb') as data:
            ports_info = yaml.load(data, Loader=yaml.FullLoader)
    
    return ports_info

def get_cam_settings(download=True):
    # Initializing cam_settings
    cam_settings = None
    if download:
        logger.info("Downloading Camera settings")
        # Service client of azure to connect to blob storage
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)

        # Holder of the config file
        blob_client = blob_service_client.get_blob_client(container=container_name, blob='Configs/camera_settings.json')

        # Writing the data in the file to local folder
        with open('./'+'camera_settings.json', 'wb') as data:
            try:
                # Downloading stream of config data
                download_stream = blob_client.download_blob()
                # Writing it in a config file
                data.write(download_stream.readall())
                # Reading the config into a JSON dict
                cam_settings = json.loads(download_stream.readall())
                # Closing the stream
                data.close()
            except azure.core.exceptions.ResourceNotFoundError:
                print("Blob not found with given name")
    else:
        with open('camera_settings.json', 'rb') as data:
            cam_settings = json.load(data)
    
    return cam_settings


def update_ports_info(ports_info, add_port=True):
    # Service client of azure to connect to blob storage
    logger.info('Updating the ports information')
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

    # Holder of the config file
    blob_client = blob_service_client.get_blob_client(container=container_name, blob='Configs/ports_info.yml')

    if add_port:
        logger.info("Adding new port information and uploading on Azure")
        with open('ports_info.yml', 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)
    else:
        logger.info("Removing port information and uploading on Azure")
        with open('ports_info.yml', 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)

def get_optimized_pipeline(cam='webcam'):

    logger.info('Getting the optimized pipeline from database')
    # Downloading the pipeline config file
    if not os.path.exists('camera_settings.json'):
        cam_settings = get_cam_settings()
    else:
        with open('camera_settings.json', 'rb') as data:
            cam_settings = json.load(data)
    
    # Getting the pipeline
    if cam == 'webcam':
        pipeline = cam_settings['webcam_pipeline']
    else:
        pipeline = cam_settings['rtsp_pipeline'] 

    logger.debug(f"Raw {cam} pipeline : {pipeline}")   

    return pipeline