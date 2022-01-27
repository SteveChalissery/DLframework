# Importing packages
from database import update_ports_info, get_cam_settings, get_optimized_pipeline
import cv2
import json
import logging
import uuid
import os
import random
import numpy as np
import yaml
import time

camera_link_thread = None

# Setting the logger information for the application
logger = logging.getLogger(__name__)
logger.setLevel( logging.DEBUG )
logging.basicConfig(format='IOP DL Logs: %(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def start_stream(camera_link, ports_info, host_ip):
    global camera_link_thread
    logger.info("Getting cam stream properties from azure")
    
    # Getting camera settings for frames
    cam_settings = get_cam_settings()
    print(cam_settings)

    # Cam properties
    fps = cam_settings['camera_settings']['fps']
    frame_width = cam_settings['camera_settings']['frame_width']
    frame_height = cam_settings['camera_settings']['frame_height']

    # Create capture
    cap = cv2.VideoCapture(camera_link)

    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    # Generate a local config file to track the camera stream initialized
    logger.info('Assigning unique ID to the camera')
    uuid_track = update_camera_track(camera_link)

    # Assign a free port to the camera
    logger.info('Assigning a free port on the host to send the frames')
    port = get_camera_port(ports_info)

    # Define the gstreamer sink
    # Getting the optimized pipeline from cloud
    gst_cam_pipeline = f'appsrc ! ' + get_optimized_pipeline() + f' ! udpsink host={host_ip} port={port}'
    logger.info(f'Complete pipeline : {gst_cam_pipeline}')

    # Create videowriter as a SHM sink
    logger.info(f'Starting to send the frame on the host_ip {host_ip} on port {port}')
    out = cv2.VideoWriter(gst_cam_pipeline, 0, fps, (frame_width, frame_height), True)

    # Flag to update once
    update_flag = True

    # Writing the return for the API
    status = {
        'status' : 'Stream Successfully Initialized',
        'host_ip': host_ip,
        'port' : port
    }
    with open('status.json', 'w') as file:
        file.write(json.dumps(status))


    # Loop it
    while True:
        # Get the frame
        ret, frame = cap.read()
        # Check
        if ret is True:
            # Write to SHM
            logger.debug(f'Sending Frame : {np.array(frame).shape}')
            out.write(frame)

            if update_flag:
                # Updating the ports_info.yml file and uploading on azure
                update_ports_info(ports_info)
                update_flag = False
            
            if camera_link_thread:
                with open("camera_uuids.json") as data:
                    camera_data = json.load(data)
                if camera_data[camera_link_thread] == uuid_track:
                    # Releasing video captures
                    cap.release()

                    # Removing the port from used ports
                    with open('ports_info.yml', 'r') as data:
                        ports_info = yaml.load(data, Loader=yaml.FullLoader)
                    ports_info['ports_used'].remove(port)

                    with open('ports_info.yml', 'w') as data:
                        yaml.dump(ports_info, data)
                    update_ports_info(ports_info, add_port=False)
                    camera_link_thread = None
                    break

        else:
            print("Camera error.")
            if camera_link_thread:
                with open("camera_uuids.json") as data:
                    camera_data = json.load(data)
                if camera_data[camera_link_thread] == uuid_track:
                    # Releasing video captures
                    cap.release()

                    # Removing the port from used ports
                    with open('ports_info.yml', 'r') as data:
                        ports_info = yaml.load(data, Loader=yaml.FullLoader)
                    ports_info['ports_used'].remove(port)

                    with open('ports_info.yml', 'w') as data:
                        yaml.dump(ports_info, data)
                    update_ports_info(ports_info, add_port=False)
                    break
            time.sleep(10)


# Function to update the camera streams initialized
def update_camera_track(camera_link):
    uuid_track = str(uuid.uuid4())
    if os.path.exists("camera_uuids.json"):
        with open("camera_uuids.json") as data:
            camera_data = json.load(data)
        camera_data[camera_link] = uuid_track

        with open("camera_uuids.json", 'w') as data:
            json.dump(camera_data, data, indent=4)
            
    else:
        camera_data = {}
        camera_data[camera_link] = uuid_track
        with open("camera_uuids.json", 'w') as data:
            json.dump(camera_data, data, indent=4)
    
    return uuid_track

def get_camera_port(ports_info):
    ports_range = ports_info['ports_range']
    port = random.randint(ports_range[0], ports_range[1])
    
    while True:
        if (port in ports_info['ports_used']) or (port in ports_info['restricted_ports']):
            port = random.randint(ports_range[0], ports_range[1])
        else:
            break

    # Updating the ports used 
    ports_info['ports_used'].append(port)
    with open('ports_info.yml', 'w') as data:
        yaml.dump(ports_info, data)

    return port

