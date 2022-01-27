# Importing packages
from azure.storage.blob import BlobServiceClient
import azure
import json

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