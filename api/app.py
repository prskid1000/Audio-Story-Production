import base64
import json
import io
import cv2
import numpy as np
import requests
import uuid
from flask import Flask, request
import time

app = Flask(__name__)

URL = 'http://127.0.0.1:8188/'

# Set CORS headers for the main request
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Max-Age": "3600",
}

def find_node_id_by_title(data, title):
  for node_id, node in data.items():
    if node['_meta']['title'] == title:
      return node_id
  return None

def upload_image_multipart(base64_image_data):
  # Decode base64 to binary
  image_data = base64.b64decode(base64_image_data)

  # Create a file-like object
  image_file = io.BytesIO(image_data)

  # Prepare multipart form data
  files = {'image': (str(uuid.uuid4()) + '.png', image_file, 'image/png')}

  # Send the request
  response = requests.post(URL + 'upload/image', files=files)

  if response.status_code == 200:
    return response.json().get('name')
  else:
    return None

def uploadImages(workflow, images):
  """{
        "node": "Node A",
        "data": "base64_image_data"
    }"""
  for image in images:
    uid = upload_image_multipart(image['data'])

    if uid is None:
      return None
    
    node_id = find_node_id_by_title(workflow, image['node'])

    if node_id is None:
        return None
    
    workflow[node_id]['inputs']['image'] = uid

  return workflow

def updateInputs(workflow, inputs):
  """{
    "node": "Node B",
    "inputs": {
      "input_1": "value",
      "input_2": "value"
    }"""
  for input in inputs:

    node_id = find_node_id_by_title(workflow, input['node'])

    if node_id is None:
        return None
    
    for key, value in input['values'].items():
        workflow[node_id]['inputs'][key] = value

  return workflow

@app.route('/workflow', methods=['OPTIONS'])
def options():
   return ("", 204, headers)

@app.route('/workflow', methods=['POST'])
def workflow():
    try:
          """{
                "images": [
                    {
                        "node": "Node A",
                        "data": "base64_image_data"
                    }
                ],
                "inputs": [
                    {
                        "node": "Node B",
                        "values": {
                            "input_1": "value",
                            "input_2": "value"
                        }
                    }
                ],
                "workflow": "try_on"
            """
          data = request.get_json()

          image_data = data['images']

          inputs = data['inputs']
              
          with open('./workflows/' + data['workflow'] + '.json', 'r') as f:
              workflow = json.load(f)
  
          workflow = uploadImages(workflow, image_data)

          if workflow is None:
              return 'Image Error', 500, headers
          
          workflow = updateInputs(workflow, inputs)

          if workflow is None:
              return 'Input Error', 500, headers
          
          response = requests.post(URL + 'prompt', json={"prompt": workflow})

          data = response.json()

          oom_count = 0
          while True:
            result = requests.get(
                "http://localhost:5000/history?prompt_id=" + data["prompt_id"]
            ).json()

            if "OutOfMemoryError" in json.dumps(result) and oom_count < 5:
                print("Retrying due to OOM")
                response = requests.post(URL + 'prompt', json={"prompt": workflow})
                data = response.json()
                oom_count = oom_count + 1
                continue

            if "status" in result:
                return result, 200, headers
            
            time.sleep(15)

    except Exception as e:
        return str(e), 500, headers

@app.route('/history', methods=['GET'])
def history():
    try:
        prompt_id = request.args.get('prompt_id')
        response = requests.get(URL + 'history/' + prompt_id)
        data = response.json()[prompt_id]
        
        images = []
        for node_id, node in data["outputs"].items():
            if node["images"]:
                for image in node["images"]:
                    with open('../ComfyUI/output/' + image['filename'], 'rb') as f:
                      image_data = base64.b64encode(f.read()).decode("utf-8")
                      images.append(image_data)


        return {"images": images, "status": data['status']}, 200, headers
    except Exception as e:
        if str(e).replace("'", "") == prompt_id:
            return {}, 200, headers
        return str(e), 500, headers

if __name__ == '__main__':
  app.run(debug=True)