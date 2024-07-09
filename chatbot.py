from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    ManagedOnlineEndpoint,
    ManagedOnlineDeployment,
    Model,
    Environment,
    CodeConfiguration,
)
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
import time
import json, os
import shutil

endpoint = ""
key = ""


registry_name = "HuggingFace"
model_name = "bert_large_uncased"
model_id = "azureml://registries/HuggingFace/models/distilbert-base-cased-distilled-squad/versions/16"
try:
    credential = DefaultAzureCredential()
    # Check if given credential can get token successfully.
    credential.get_token("https://management.azure.com/.default")
except Exception as ex:
    # Fall back to InteractiveBrowserCredential in case DefaultAzureCredential not work
    # This will open a browser page for
    credential = InteractiveBrowserCredential(tenant_id="cd03c904-e918-4d7c-908b-54602d4cd12e")



#ml_client=MLClient(credential=credential,workspace_name="Qna",subscription_id="008``9576c-ac22-4b94-8303-43029ff93a88",resource_group="GenAI")

try:
    ml_client = MLClient.from_config(credential=credential)
except Exception as ex:
    # NOTE: Update following workspace information to contain
    #       your subscription ID, resource group name, and workspace name
    client_config = {
       "subscription_id": "",
        "resource_group": "GenAI",
        "workspace_name": "Qna"

 }
    config_path = "../.azureml/config.json"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as fo:
        fo.write(json.dumps(client_config))
    ml_client = MLClient.from_config(credential=credential, path=config_path)

endpoint_name="c1-h1" + str(int(time.time())) # endpoint name must be unique per Azure region, hence appending timestamp

ml_client.begin_create_or_update(ManagedOnlineEndpoint(name=endpoint_name)).wait()
ml_client.online_deployments.begin_create_or_update(ManagedOnlineDeployment(
    name="chatbot",
    endpoint_name=endpoint_name,
    model=model_id,
    instance_type="Standard_E2s_v3",
    instance_count=2,
)).wait()

endpoint = ml_client.online_endpoints.get(endpoint_name)
endpoint.traffic = {"chatbot": 100}
ml_client.begin_create_or_update(endpoint).result()









