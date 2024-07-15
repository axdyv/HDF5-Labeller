from flask import Flask, request, send_from_directory, jsonify, send_file
from flask_cors import CORS, cross_origin
import h5py
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import math
import os
import shutil
from io import BytesIO
import zipfile
import pylev

app = Flask(__name__,)
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
METADATA_FOLDER = 'metadata'
isHDF5 = False
isDicom = False
labels = {}

def setup_folders():
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
    if os.path.exists('outputView'):
        shutil.rmtree('outputView')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs('outputView', exist_ok=True)
    labels = {}
    


# Upload/output Routes
@app.route('/output-files', methods=['GET'])
@cross_origin()
def list_output_files():
    path = request.args.get('path', '')
    VISUALIZATION_FOLDER = 'output'
    uploads_folder = 'uploads'
    if os.path.isdir(uploads_folder) and os.listdir(uploads_folder):
        first_file = os.path.join(uploads_folder, os.listdir(uploads_folder)[0])
        if os.path.isfile(first_file) and zipfile.is_zipfile(first_file):
            VISUALIZATION_FOLDER = 'outputView'
    directory = os.path.join(VISUALIZATION_FOLDER, path)
    if not os.path.exists(directory):
        return jsonify({'error': 'Directory not found'}), 404

    files = os.listdir(directory)
    return jsonify(files)

@app.route('/output-files/<path:filename>', methods=['GET'])
@cross_origin()
def get_output_file(filename):
    VISUALIZATION_FOLDER = 'output'
    uploads_folder = 'uploads'
    if os.path.isdir(uploads_folder) and os.listdir(uploads_folder):
        first_file = os.path.join(uploads_folder, os.listdir(uploads_folder)[0])
        folder_path = os.path.join(VISUALIZATION_FOLDER, filename)
        if os.path.isfile(first_file) and zipfile.is_zipfile(first_file):
            VISUALIZATION_FOLDER = 'outputView'
            folder_path = os.path.join(VISUALIZATION_FOLDER, filename)
            return send_file(folder_path)
    print("output file path: " + folder_path)
    return send_file(folder_path)

@app.route('/output-files/download-folder', methods=['GET'])
@cross_origin()
def download_folder():
    folder_path = request.args.get('folder')
    if not folder_path:
        return jsonify({'error': 'Folder parameter is required'}), 400

    folder_path = os.path.join(OUTPUT_FOLDER, folder_path)
    if not os.path.isdir(folder_path):
        return jsonify({'error': 'Folder not found'}), 404

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.relpath(file_path, folder_path))

    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name=f'{os.path.basename(folder_path)}.zip')

@app.route('/upload', methods=['POST'])
@cross_origin()
def upload_file():
    setup_folders()

    if 'file' not in request.files or len(request.files) != 1:
        return jsonify({'error': 'Please upload exactly one file'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if allowed_file(file.filename):
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        if file.filename.lower().endswith(('.h5', '.hdf5')):
            mainHDF5Method(file_path)
        else:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall('uploads/dicomImages')
            
            mainDICOMMethod('uploads/dicomImages', OUTPUT_FOLDER)

        return jsonify({
            'message': 'File successfully uploaded and processed',
            'file_name': file.filename,
            'file_size': os.path.getsize(file_path),
            'file_path': file_path
        }), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400

@app.route('/output-files/folder-images', methods=['GET'])
@cross_origin()
def get_folder_images():
    VISUALIZATION_FOLDER = 'output'
    uploads_folder = 'uploads'

    if os.path.isdir(uploads_folder) and os.listdir(uploads_folder):
        first_file = os.path.join(uploads_folder, os.listdir(uploads_folder)[0])
        if os.path.isfile(first_file) and zipfile.is_zipfile(first_file):
            VISUALIZATION_FOLDER = 'outputView'

    folder_path = request.args.get('folder')
    if not folder_path:
        app.logger.error("Folder parameter is required")
        return jsonify({'error': 'Folder parameter is required'}), 400

    full_folder_path = os.path.join(VISUALIZATION_FOLDER, folder_path)
    app.logger.debug(f"Looking for images in: {full_folder_path}")

    if not os.path.isdir(full_folder_path):
        app.logger.error(f"Folder not found: {full_folder_path}")
        return jsonify({'error': 'Folder not found'}), 404

    image_files = [file for file in os.listdir(full_folder_path) if file.endswith(('.jpg', '.jpeg', '.png'))]
    image_urls = [f"http://127.0.0.1:5000/output/{folder_path}/{file}" for file in image_files]
    app.logger.debug(f"Image URLs: {image_urls}")

    return jsonify(image_urls)

@app.route('/output/<path:folder>/<path:image>', methods=['GET'])
@cross_origin()
def get_image_file(folder, image):
    VISUALIZATION_FOLDER = 'output'
    uploads_folder = 'uploads'

    if os.path.isdir(uploads_folder) and os.listdir(uploads_folder):
        first_file = os.path.join(uploads_folder, os.listdir(uploads_folder)[0])
        if os.path.isfile(first_file) and zipfile.is_zipfile(first_file):
            VISUALIZATION_FOLDER = 'outputView'

    folder_path = os.path.join(VISUALIZATION_FOLDER, folder, image)
    app.logger.debug(f"Serving image from path: {folder_path}")

    if not os.path.isfile(folder_path):
        app.logger.error(f"Image file not found: {folder_path}")
        return jsonify({'error': 'Image file not found'}), 404

    return send_file(folder_path)

# New route to view folder contents as JSONs
@app.route('/output-files/folder-metadata-text', methods=['GET'])
@cross_origin()
def get_folder_metadata_text():
    VISUALIZATION_FOLDER = 'output'
    uploads_folder = 'uploads'
    
    # Check if the upload folder contains a zip file
    if os.path.isdir(uploads_folder) and os.listdir(uploads_folder):
        first_file = os.path.join(uploads_folder, os.listdir(uploads_folder)[0])
        if os.path.isfile(first_file) and zipfile.is_zipfile(first_file):
            VISUALIZATION_FOLDER = 'outputView'
    
    # Get the folder path from the request
    folder_path = request.args.get('folder')
    if not folder_path:
        app.logger.error("Folder parameter is required")
        return jsonify({'error': 'Folder parameter is required'}), 400

    # Construct the full path to the folder
    full_folder_path = os.path.join(VISUALIZATION_FOLDER, folder_path)
    app.logger.debug(f"Looking for metadata and text files in: {full_folder_path}")

    # Check if the folder exists
    if not os.path.isdir(full_folder_path):
        app.logger.error(f"Folder not found: {full_folder_path}")
        return jsonify({'error': 'Folder not found'}), 404

    # Find metadata and text files
    metadata_files = [file for file in os.listdir(full_folder_path) if file.endswith('.json')]
    text_files = [file for file in os.listdir(full_folder_path) if file.endswith('.txt')]

    # Read the contents of the metadata files
    metadata_contents = {}
    for metadata_file in metadata_files:
        file_path = os.path.join(full_folder_path, metadata_file)
        with open(file_path, 'r') as file:
            try:
                metadata_contents[metadata_file] = json.load(file)
            except json.JSONDecodeError as e:
                app.logger.error(f"Error decoding JSON from file {file_path}: {e}")
                metadata_contents[metadata_file] = {"error": "Invalid JSON file"}

    # Read the contents of the text files
    text_contents = {}
    for text_file in text_files:
        file_path = os.path.join(full_folder_path, text_file)
        with open(file_path, 'r') as file:
            text_contents[text_file] = file.read()

    # Return the combined contents as a JSON response
    return jsonify({
        'metadata': metadata_contents,
        'text': text_contents
    })

# End of Upload/Output routes

@app.route('/save-label', methods=['POST'])
@cross_origin()
def save_label():
    data = request.get_json()

    # Debug log to check if we are receiving data
    app.logger.debug(f"Received data: {data}")

    filename = data.get('filename')
    print(filename)
    label = data.get('label')

    if not filename or not label:
        app.logger.error("Invalid data: Missing filename or label")
        return jsonify({"error": "Filename and label are required"}), 400

    # Save the label associated with the filename
    if (filename != "nestedDict.json"):
        labels[filename] = label
    app.logger.debug(f"Label saved: {filename} -> {label}")
    numFilesToLabel = len(os.listdir('output')) - 1
    app.logger.debug(f"numFilesToLabel: {numFilesToLabel}")
    output_json_path = os.path.join("labelInfo", "firstFile.json")
    app.logger.debug(f"numLabels: {len(labels)}")

    if (len(labels) == numFilesToLabel):
        if (not os.path.isfile(output_json_path)):
            os.makedirs("labelInfo", exist_ok=True)
            with open(output_json_path, 'w') as json_file:
                json.dump(labels, json_file, indent=True)
        else:
            # compare similarity of images, labels, and data
            app.logger.debug(f"came into else")
            with open(os.path.join("labelInfo", "firstFile.json"), 'r') as filePath:
                ogDict = json.load(filePath)
            print(ogDict)
            print(labels)
            ogImages = 0
            newImages = 0
            ogLabels = 0
            newLabels = 0
            ogData = 0
            newData = 0
            for files in ogDict.values():
                if (files == "images"):
                    ogImages += 1
                if (files == "labels"):
                    ogLabels += 1
                if (files == "data"):
                    ogData += 1
            for files in labels.values():
                if (files == "images"):
                    newImages += 1
                if (files == "labels"):
                    newLabels += 1
                if (files == "data"):
                    newData += 1
            app.logger.debug(f"ogImages: {ogImages}")
            app.logger.debug(f"newImages: {newImages}")
            app.logger.debug(f"ogLabels: {ogLabels}")
            app.logger.debug(f"newLabels: {newLabels}")
            app.logger.debug(f"ogData: {ogData}")
            app.logger.debug(f"newData: {ogData}")
            print(abs(ogImages - newImages) + abs(ogLabels - newLabels) + abs(ogData - newData))

                

    return jsonify({"message": "Label saved successfully"}), 200

@app.route('/get-labels', methods=['GET'])
@cross_origin()
def get_labels():
    labels_file = 'labels.json'

    if os.path.exists(labels_file):
        with open(labels_file, 'r') as f:
            labels_data = json.load(f)
        return jsonify(labels_data)
    else:
        return jsonify({}), 200


# HDF5 Parser
def mainHDF5Method(file_path):
    isHDF5 = True
    path_to_dataset = {}
    with h5py.File(file_path, 'r') as file:
        file.visititems(lambda name, obj: traverse_hdf5(name, obj, path_to_dataset))

    output_json_path = os.path.join('output', 'nestedDict.json')
    with open(output_json_path, 'w') as json_file:
        json.dump(path_to_dataset, json_file, indent=True)

def traverse_hdf5(name, obj, path_to_dataset):
    if isinstance(obj, h5py.Group):
        if '/' in name:
            current_dict = path_to_dataset
            folders = name.split('/')
            for folder in folders[:-1]:
                current_dict = current_dict.setdefault(folder, {})
            current_dict[folders[-1]] = {}
        else:
            path_to_dataset[name] = {}
    elif isinstance(obj, h5py.Dataset):
        current_dict = path_to_dataset
        filePath = ""
        folders = name.split('/')
        for folder in folders[:-1]:
            current_dict = current_dict.setdefault(folder, {})
            filePath = filePath + folder
        dataset_name = folders[-1]

        if (("X" in name or "data" in name or "image" in name) and obj.ndim >= 2):
            image_folder = os.path.join('output', filePath + dataset_name + "Images")
            os.makedirs(image_folder, exist_ok=True)
            imageDatasetHandling(obj, image_folder)
            current_dict[dataset_name] = image_folder
        elif obj.ndim >= 2:
            data_path = os.path.join('output', filePath + dataset_name + "Data.npy")
            np.save(data_path, np.array(obj))
            current_dict[dataset_name] = data_path
        elif obj.ndim == 1:
            labels_path = os.path.join('output', filePath + dataset_name + "Labels.json")
            save_labels(obj, labels_path)
            current_dict[dataset_name] = labels_path

def save_labels(obj, labels_path):
    labels = np.array(obj)
    num_images = labels.shape[0]
    label_dict = {}

    for i in range(num_images):
        if isinstance(labels[i], bytes):
            label = labels[i].decode()
        elif isinstance(labels[i], str):
            label = labels[i]
        else:
            label = int(labels[i])
        label_dict[f"img{i}.jpg"] = label

    with open(labels_path, 'w') as json_file:
        json.dump(label_dict, json_file, indent=True)

def imageDatasetHandling(dataset, folder_name):
    dataset = np.array(dataset)
    dataset = np.abs(dataset)
    scale_down = np.max(dataset) > 1

    if scale_down:
        dataset = dataset / 255.0

    size_of_dataset = dataset.shape[0]
    for i in range(size_of_dataset):
        image = dataset[i]
        if dataset.ndim == 2:
            image = image.reshape(int(math.sqrt(dataset.shape[1])), int(math.sqrt(dataset.shape[1])))
        plt.imsave(os.path.join(folder_name, f"img{i}.jpg"), image)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'h5', 'hdf5', 'dcm', 'dicom', 'nii', 'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(debug=True)
