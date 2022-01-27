import json
import logging
from logging.handlers import RotatingFileHandler
from database import connect_str, container_name
from azure.storage.blob import BlobServiceClient, BlobClient
import requests
from datetime import datetime

# Function to initialize the logging service
def logger(readfile):
    '''
    Function to load the logging configuration of the IOP application.
    Parameters:
        Input:
            None: Function does not take any input arguments
        Output:
            logger: Logging object for the service
    '''

    # Getting the file handler for log
    logHandler = RotatingFileHandler(readfile["logfileName"], mode='a', backupCount=5, encoding=None, delay=False)
    
    # Format for the log
    logFormatter = logging.Formatter('[%(levelname)s]\t: %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logHandler.setFormatter( logFormatter )
    
    # Logger object
    logger = logging.getLogger('DL-Framework')
    logger.addHandler( logHandler )

    # Setting the logging level
    logLevel = readfile['loglevel']
    numeric_level = getattr(logging, logLevel.upper(), 10) # readfile["loglevel"]
    logger.setLevel(level=numeric_level)

    return logger

# Function to upload the logfile to the Azure blob
def log_function(logger, readfile):
    '''
    Function to upload the logs in Azure Blob.
    Parameters:
        Input:
            value: 
            logger: Logging object
            readfile: JSON Object containing information about the logger settingd
        Output:
            logger: Logging object for the service
    '''
    try:
        logHeader = eval(readfile["logHeader"])
        file = open(readfile["logfileName"])
        file_data = file.read()
        words = file_data.split(" ")
        date = words[1].replace("-","")
        file.close()
        log_request = {"logdate": date, "logdata": file_data}
        log_json = json.dumps(log_request)
    except:
        logger.exception('Could not read logfile')
        print("Could not read logfile")
    try:
        response = requests.post(readfile["logURL"], data=log_json, verify=False, headers=logHeader)
        print(response.status_code)
    except requests.Timeout as time:
        logger.exception('Logger Service failed to respond')
        print("Logger Service failed to respond")
    
    try:
        f = open(readfile["logfileName"], "a")
        f.truncate(0)
        f.close()
    except Exception as e:
        logger.exception('Could not empty logfile')
        print("Could not empty logfile")