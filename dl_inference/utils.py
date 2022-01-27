# Import packages
import json
from database import get_azure_config
import os
import azure
from azure.storage.blob import BlobServiceClient


# Getting azure credentials
oiazurecred = get_azure_config()

with open('OIConfig.json', 'rb') as data:
    oiconfig = json.load(data)


def get_deployement_details():

    # Initializing return variables
    unique_id = ""
    model_name = ""
    scoring_uri = ""
    access_keys = []

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
        except azure.core.exceptions.ResourceNotFoundError:
            raise exception.ResourceNotFound


    if (os.path.exists(f"DeployConfig.json")):
        with open('DeployConfig.json', 'rb') as data:
        
            deployData = json.loads(data.readlines()[0])
            unique_id = deployData['unique_id']
            model_name = deployData['Model Name']
            scoring_uri = deployData['scoring_uri'],
            access_keys = deployData['API_Keys']

    return (unique_id, model_name, scoring_uri, access_keys)