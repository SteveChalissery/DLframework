# Importing Packages
import json
from database import get_azure_config
from azureml.core.authentication import ServicePrincipalAuthentication
from azureml.core import Workspace, Experiment, Run, Datastore
from azureml.core.compute import ComputeTarget, AmlCompute
from azureml.core.compute_target import ComputeTargetException
from azureml.core.runconfig import RunConfiguration, DataReferenceConfiguration, ContainerRegistry
from azureml.core import ScriptRunConfig
import datetime
import os
from azureml.widgets import RunDetails

# Getting azure credentials
oiazurecred = get_azure_config()

with open('OIConfig.json', 'rb') as data:
    oiconfig = json.load(data)

# Function to authenticate to the AML workspace
def workspace_authentication(train_config, ws_only=False):

    # Getting the azure credentials 
    subscription_id = oiazurecred['subscription_id']
    resource_group = oiazurecred['resource_group']
    workspace_name = oiazurecred['workspace_name']
    
    # Connecting to the workspace
    sp = ServicePrincipalAuthentication(tenant_id="b2b31fd7-64c7-49ba-bb99-9069b9dc0537", # tenantID
                                    service_principal_id="dbafd8e5-5b1d-412f-9d39-ff1e4738d7cb", # clientId
                                    service_principal_password="Y62uDg91oTcaaEy-b~On_N_CG0ugea3D8~") # clientSecret

    workspace = Workspace(subscription_id=subscription_id,
                resource_group=resource_group,
                workspace_name=workspace_name,
                auth=sp)
    # workspace = Workspace.from_config()

    if ws_only:
        return workspace
    
    # Creating compute targets if not already created
    if train_config['GPU']:
        cluster_name = oiazurecred["compute_gpu"] + str(train_config['GPU_COUNT'])
    else:
        cluster_name = oiazurecred["compute_cpu"] + str(train_config['CPU_COUNT'])
    try:
        compute_target = ComputeTarget(workspace=workspace, name=cluster_name)
        print('Found existing compute target')
    except ComputeTargetException:
        if train_config['GPU']:
            print('Creating a new compute target...')
            compute_config = AmlCompute.provisioning_configuration(vm_size=oiazurecred['GPU_SKU'], 
                                                                max_nodes=24)

            compute_target = ComputeTarget.create(workspace, cluster_name, compute_config)

            compute_target.wait_for_completion(show_output=True, min_node_count=None, timeout_in_minutes=20)
        else:
            print('Creating a new compute target...')
            compute_config = AmlCompute.provisioning_configuration(vm_size=oiazurecred['CPU_SKU'], 
                                                                max_nodes=16)

            compute_target = ComputeTarget.create(workspace, cluster_name, compute_config)

            compute_target.wait_for_completion(show_output=True, min_node_count=None, timeout_in_minutes=20)

    return workspace

# Functino to start the training process
def initiate_training(workspace, train_config):
    # Initializing and retrieving datastores
    dr, drlogs, ds, dslogs = mount_aml_datastore(workspace, train_config) 

    # Setting the compute name and target
    if train_config['GPU']:
        compute_name = oiazurecred["compute_gpu"] + str(train_config['GPU_COUNT'])
    else:
        compute_name = oiazurecred["compute_cpu"] + str(train_config['CPU_COUNT'])
    compute_target = workspace.compute_targets[compute_name]

    print(compute_name, compute_target)

    # Creating Experiment for running all the trainings
    experiment_name = oiazurecred['experiment']
    experiment = Experiment(workspace=workspace, name=experiment_name)

    # Docker image related information
    image_registry_details = ContainerRegistry()
    image_registry_details.address = train_config['DOCKER_REGR_ADDR']
    image_registry_details.username = train_config['DOCKER_REGR_NAME']
    image_registry_details.password = train_config['DOCKER_REGR_PASS']
    training_docker_image = train_config['DOCKER_REGR_ADDR'] + '/' + train_config['DOCKER_TRAIN_IMAGE']

    # Getting the run configurations
    run_config = get_run_config(train_config, image_registry_details,
                                training_docker_image, dr, drlogs,
                                ds, dslogs, compute_target)


    # Initializing the training process
    currentDT = datetime.datetime.now()
    currentDTstr = "AppData/" + train_config['UID'] + "/" + "logs" + "/" + currentDT.strftime("%Y%m%d_%H%M")
    print('logs will be in {}'.format(currentDTstr))

    # Base mount
    base_mount = ds.as_mount()
    # Directory where the base model selected by user is stored. Internal Model Zoo
    base_model_dir = os.path.join(str(base_mount), train_config['MODELS_SUBDIR'], train_config['BASE_MODEL'])
    # Directory where the tfrecord files are stored.
    tfrecords_dir = os.path.join(str(base_mount), train_config['TFRECORDS_SUBDIR'])
    # Output Directory
    output_dir = os.path.join(str(base_mount), train_config['MODEL_DIR'])

    print(base_mount)
    print(base_model_dir)
    print(tfrecords_dir)
    print(output_dir)

    # Logging directory
    logs_mount = dslogs.as_mount()
    logs_dir = os.path.join(str(logs_mount), currentDTstr)

    # Creating the parameters for the entry script
    script_params = [
        '--base_model_dir', base_model_dir, 
        '--tfrecords_dir', tfrecords_dir,
        '--force_regenerate_tfrecords', False,
        '--num_steps', train_config['EPOCHS'],
        '--log_dir', logs_dir,
        '--classname_in_filename', False,
        '--output_dir', output_dir ,
        '--learning_rate', float(train_config['LR']),
        '--batch_size', train_config['BATCH_SIZE'],
        '--data_augment_options', train_config['AUGMENT'],
    ]

    # Configuring the script
    src = ScriptRunConfig(source_directory = train_config['SCRIPT_FOLDER'],
                      script = train_config['SCRIPT_FILE'], 
                      run_config = run_config,
                      arguments=script_params)


    

    run = experiment.submit(src)
    print('run details {}'.format(run.get_details))
    return run

    
# Function to initialize the running configurations for the scripts
def get_run_config(config, registry, docker_img, dr, drlogs, ds, dslogs, compute_target):
    # Initializing the RunConfiguration object
    run_cfg = RunConfiguration()
    # Enabling docker image
    run_cfg.environment.docker.enabled = True
    # GPU support
    run_cfg.environment.docker.gpu_support = True if config['GPU'] else False
    # Training docker image 
    run_cfg.environment.docker.base_image = docker_img # docker image fullname
    # Registry details of the ACR
    run_cfg.environment.docker.base_image_registry = registry
    # Mount references
    run_cfg.data_references = {ds.name: dr, dslogs.name: drlogs}
    run_cfg.environment.python.user_managed_dependencies = True
    run_cfg.target = compute_target

    return run_cfg


# Function to mount datastores in AML
def mount_aml_datastore(ws, config):

    if oiazurecred['proj_datastore'] is None:
        ds = ws.get_default_datastore()
    else:
        ds = Datastore.get(ws, datastore_name=oiazurecred['proj_datastore'])

    dslogs = Datastore.get(ws, datastore_name=oiazurecred['logs_datastore'])
    print(ds.container_name, dslogs.container_name)

    # Default model datastores
    dr = DataReferenceConfiguration(datastore_name=ds.name, 
                                path_on_datastore=config['proj_root'],
                                overwrite=True)
    # Log datastores
    drlogs = DataReferenceConfiguration(datastore_name=dslogs.name, 
                                    path_on_datastore=config['proj_root'],
                                    overwrite=True)
    return dr, drlogs, ds, dslogs


#Functinon to clean the created resources
def clean_azure_resources(target, ws):
    # Getting the compute instance
    computeInstance = ws.compute_targets[target]
    # Deleting the cluster
    computeInstance.delete()

# Worker function to update the status
def status_updater(run, train_config):

    # Until False run the loop
    while True:
        # Returning the run status
        status =  run.get_detailed_status()
        widget_details = RunDetails(run).get_widget_data()

        # Getting the running logs from azureml
        logs = widget_details['run_logs']

        # Splitting into list
        logs = logs.split()

        # Initializing empty lists
        step_list = []
        loss_list = [] 
        
        # Extracting the steps and loss from running logs
        if logs:
            for index, ch in enumerate(logs):
                if ch == "step":
                    step_list.append(logs[index+1].strip(":"))
                if ch == "loss":
                    loss_list.append(logs[index+2])   

            if step_list and loss_list:
                step_list = [float(x) for x in step_list]
                loss_list = [float(x) for x in loss_list]

                # Converting into uique set and then again to list
                steps = list(set(step_list))
                loss = list(set(loss_list)) 

                # Updating the status after completion of training
                if len(steps) >= train_config['EPOCHS']-5:
                    # Saving the status in a JSON file
                    with open(str(run.id) + '_status.json', 'w') as data:
                        # Creating response dict
                        response_dict = {
                            'status' : "Completed",
                            'loss' : loss,
                            'response' : {}
                        }
                        data.write(json.dumps(response_dict))
                        data.close()

                    break 

# Function to update the status 
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
