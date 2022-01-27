# Importing packages
from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from database import get_OI_config, get_azure_config, get_ports_info
from utils import start_stream
import utils
from threading import Thread
import logging
import time
import json

# Creating the app
app = Flask(__name__)

# Initiating the API
api = Api(app)

# Application configuration
# app.config['CORS_HEADERS'] = oiConfig["CORS_HEADERS"]
app.config['JSON_SORT_KEYS'] = False


# Setting the logger information for the application
logger = logging.getLogger(__name__)
logger.setLevel( logging.DEBUG )
logging.basicConfig(format='IOP DL Logs: %(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


class StreamInitializer(Resource):
    """
        Class holding the structure and functions needed to encode camera feeds and stream over
        network
    """ 

    # Constructor of anomaly class
    def __init__(self):
        '''
        Constructor to initialize variables in the anomaly flask service
        '''
        logger.info("Initializing the streaming class")
        self.camera_link = request.get_json()['camera_link']
        logger.info(f'Camera link : {self.camera_link}')

        self.host_ip = request.get_json()['IPADDRR']
        logger.info(f'Host IP address : {self.host_ip}')


    def post(self):
        logger.info('Starting stream encoding from camera feeds')
        logger.info("Getting ports_info.yml file from azure blob storage.")
        
        # Getting the ports used
        ports_info = get_ports_info()
        logger.info(f"Ports Information: {ports_info}")


        # Starting a thread for sending the video frames
        thread = Thread(target=start_stream, kwargs={'camera_link': request.args.get('camera_link', self.camera_link),
                                                       'ports_info' : request.args.get('ports_info', ports_info),
                                                       'host_ip' : request.args.get('host_ip', self.host_ip)})
        
        thread.setDaemon(True) 
        thread.start()

        time.sleep(5)
        with open('status.json', 'r') as file:
            status = json.loads(file.readlines()[0])
        return status

class StopThreads(Resource):
    def get(self):
        logger.info(f"Stoping the frame for camera : {request.get_json()['camera_link']}")
        utils.camera_link_thread = request.get_json()['camera_link']
        return f"{request.get_json()['camera_link']} has stopped sending frames"

if __name__ == "__main__":

    # Downloading azure and application configs
    # Getting the OI config file for configurations
    oiConfig = get_OI_config()

    # Getting the azure credentials from Azure
    oiazurecred = get_azure_config()

    # Initializing the app service
    api.add_resource(StreamInitializer, "/initiateStream")
    api.add_resource(StopThreads, "/stop_thread")
    app.run(host=oiConfig['host'], port=oiConfig['port'], threaded=True, debug=True)
