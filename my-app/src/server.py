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
from collections import deque
import time
import pydicom
import nibabel as nib

app = Flask(__name__,)
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
METADATA_FOLDER = 'metadata'
isHDF5 = False
isDicom = False
labels = {}
labelsFinished = {}
labelsForView = {}

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
    print("directory = " + directory)
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
        elif file.filename.lower().endswith(('.dcm', '.dicom')):
            mainDICOMMethod('uploads', OUTPUT_FOLDER)
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

@app.route('/sample-upload', methods=['POST'])
@cross_origin()
def upload_sample_file():
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    setup_folders()
    labels = {}
    labelsFinished = {}
    if os.path.exists('labelInfo'):
        shutil.rmtree('labelInfo')

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

@app.route('/get-labels', methods=['GET'])
@cross_origin()
def get_data():
    print("came into get data")
    print(labels)
    return jsonify(labels)

@app.route('/save-label', methods=['POST'])
@cross_origin()
def save_label():
    try:
        data = request.get_json()
        labelsFinished = data.get('filesToLabel')
        print(labelsFinished)
        if not labelsFinished:
            return jsonify({"message:"})
        
        with open('labelInfo/fileLabels.json', 'w') as file:
            json.dump(labelsFinished, file)
        
        return jsonify({"message": "Labels saved successfully"}), 200
    except Exception as e:
        return jsonify({"message": "An error occurred: {str(e)}"}), 500

FIELDS = [
    'AccessionNumber', 'AcquisitionMatrix', 'B1rms', 'BitsAllocated', 'BitsStored', 'Columns',
    'ConversionType', 'DiffusionBValue', 'DiffusionGradientOrientation', 'EchoNumbers', 'EchoTime',
    'EchoTrainLength', 'FlipAngle', 'HighBit', 'HighRRValue', 'ImageDimensions', 'ImageFormat',
    'ImageGeometryType', 'ImageLocation', 'ImageOrientation', 'ImageOrientationPatient', 'ImagePosition',
    'ImagePositionPatient', 'ImageType', 'ImagedNucleus', 'ImagingFrequency', 'InPlanePhaseEncodingDirection',
    'InStackPositionNumber', 'InstanceNumber', 'InversionTime', 'Laterality', 'LowRRValue', 'MRAcquisitionType',
    'MagneticFieldStrength', 'Modality', 'NumberOfAverages', 'NumberOfPhaseEncodingSteps', 'PatientID',
    'PatientName', 'PatientPosition', 'PercentPhaseFieldOfView', 'PercentSampling', 'PhotometricInterpretation',
    'PixelBandwidth', 'PixelPaddingValue', 'PixelRepresentation', 'PixelSpacing', 'PlanarConfiguration',
    'PositionReferenceIndicator', 'PresentationLUTShape', 'ReconstructionDiameter', 'RescaleIntercept',
    'RescaleSlope', 'RescaleType', 'Rows', 'SAR', 'SOPClassUID', 'SOPInstanceUID', 'SamplesPerPixel',
    'SeriesDescription', 'SeriesInstanceUID', 'SeriesNumber', 'SliceLocation', 'SliceThickness',
    'SpacingBetweenSlices', 'SpatialResolution', 'SpecificCharacterSet', 'StudyInstanceUID', 'TemporalResolution',
    'TransferSyntaxUID', 'TriggerWindow', 'WindowCenter', 'WindowWidth'
]

def convert_to_jpg(image_data, output_path):
    plt.imshow(image_data, cmap=plt.cm.bone)
    plt.axis('off')
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
    plt.close()

def extract_dicom_metadata(dicom_path):
    ds = pydicom.dcmread(dicom_path)
    metadata = {}
    for field in FIELDS:
        if hasattr(ds, field):
            metadata[field] = str(getattr(ds, field))
    return metadata

def convert_np_float32(obj):
    if isinstance(obj, np.float32):
        return float(obj)
    raise TypeError

def extract_nifti_metadata(nifti_path):
    img = nib.load(nifti_path)
    header = img.header
    metadata = {
        "dim": header.get_data_shape(),
        "datatype": header.get_data_dtype().name,
        "voxel_size": header.get_zooms(),
        "descrip": header['descrip'].item().decode('utf-8'),
        "xyzt_units": header.get_xyzt_units(),
        "qform_code": int(header['qform_code']),
        "sform_code": int(header['sform_code']),
    }
    for key, value in metadata.items():
        if isinstance(value, np.float32):
            metadata[key] = float(value)
    return metadata

def create_output_structure(input_folder, output_folder):
    for root, dirs, files in os.walk(input_folder):
        for dir_name in dirs:
            relative_path = os.path.relpath(os.path.join(root, dir_name), input_folder)
            os.makedirs(os.path.join(output_folder, relative_path, 'image'), exist_ok=True)
            os.makedirs(os.path.join(output_folder, relative_path, 'meta'), exist_ok=True)
            os.makedirs(os.path.join(output_folder, relative_path, 'text'), exist_ok=True)

def process_files(input_folder, output_folder):
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            file_path = os.path.join(root, file)

            if file.endswith('.dcm'):
                relative_path = os.path.relpath(root, input_folder)

                image_name = os.path.splitext(file)[0] + '.jpg'
                image_output_path = os.path.join(output_folder, relative_path, 'image', image_name.replace("./", ''))
                meta_output_path = os.path.join(output_folder, relative_path, 'meta', os.path.splitext(file)[0] + '.json')
                text_output_path = os.path.join(output_folder, relative_path, 'text', 'file.txt')

                os.makedirs(os.path.dirname(image_output_path), exist_ok=True)

                ds = pydicom.dcmread(file_path)
                convert_to_jpg(ds.pixel_array, image_output_path)

                metadata = extract_dicom_metadata(file_path)

                with open(meta_output_path, 'w') as meta_file:
                    json.dump(metadata, meta_file, default=convert_np_float32, indent=4)

                os.makedirs(os.path.dirname(text_output_path), exist_ok=True)
                with open(text_output_path, 'a') as text_file:
                    text_file.write(f'{{"{image_name}": "{os.path.basename(meta_output_path)}"}}\n')

            elif file.endswith('.nii') or file.endswith('.nii.gz'):
                try:
                    img = nib.load(file_path)
                except nib.filebasedimages.ImageFileError:
                    print(f"Skipping file: {file_path} - Not a valid NIfTI file")
                    continue

                relative_path = os.path.relpath(root, input_folder)
                image_name = os.path.splitext(file)[0] + '.jpg'
                image_output_path = os.path.join(output_folder, relative_path, 'image', image_name.replace("./", ''))
                meta_output_path = os.path.join(output_folder, relative_path, 'meta', os.path.splitext(file)[0] + '.json')
                text_output_path = os.path.join(output_folder, relative_path, 'text', 'file.txt')

                os.makedirs(os.path.dirname(image_output_path), exist_ok=True)

                data = img.get_fdata()
                middle_slice = data[:, :, data.shape[2] // 2]

                convert_to_jpg(middle_slice, image_output_path)

                metadata = extract_nifti_metadata(file_path)

                with open(meta_output_path, 'w') as meta_file:
                    json.dump(metadata, meta_file, default=convert_np_float32, indent=4)

                os.makedirs(os.path.dirname(text_output_path), exist_ok=True)
                with open(text_output_path, 'a') as text_file:
                    text_file.write(f'{{"{image_name}": "{os.path.basename(meta_output_path)}"}}\n')

def delete_empty_folders(): 
    root = 'output'
    deleted = set()
    for current_dir, subdirs, files in os.walk(root, topdown=False):

        still_has_subdirs = False
        for subdir in subdirs:
            if os.path.join(current_dir, subdir) not in deleted:
                still_has_subdirs = True
                break
        if not any(files) and not still_has_subdirs:
            os.rmdir(current_dir)
    return deleted

def output_for_visualization():
    i = 0
    for dirpath, dirnames, files in os.walk('output'):
        for dir in dirnames:
            if (dir == 'image'):
                print(os.path.join(dirpath, dir))
                shutil.copytree(os.path.join(dirpath, dir), os.path.join('outputView', 'imageNew' + str(i)))
            if (dir == 'meta'):
                print(os.path.join(dirpath, dir))
                shutil.copytree(os.path.join(dirpath, dir), os.path.join('outputView', 'metaNew' + str(i)))
            if (dir == 'text'):
                print(os.path.join(dirpath, dir))
                shutil.copytree(os.path.join(dirpath, dir), os.path.join('outputView','textNew' + str(i)))
                i += 1
    return 0

def mainDICOMMethod(input_folder, output_folder):
    isDicom = True
    isExist = os.path.exists('outputView')
    if(isExist):
        print("outputView exists")
    else:
        os.mkdir('outputView')
    create_output_structure(input_folder, output_folder)
    process_files(input_folder, output_folder)
    delete_empty_folders()
    output_for_visualization()

    shutil.rmtree("uploads/dicomImages")

# HDF5 Parser
def mainHDF5Method(file_path):
    isHDF5 = True
    labels.clear()
    labelsFinished.clear()
    if (not os.path.exists("labelInfo/sampleStructure.json")):
        # create a format based on sample file and ask user to annotate labels
        os.makedirs("labelInfo")
        path_to_dataset = {}
        with h5py.File(file_path, 'r') as file:
            file.visititems(lambda name, obj: sample_file_traversal(name, obj, path_to_dataset, True))
        output_json_path = os.path.join('labelInfo', 'sampleStructure.json')
        with open(output_json_path, 'w') as json_file:
            json.dump(path_to_dataset, json_file, indent=True)
        print("created labels")
    else:
        # time to verify and parse the new file
        with open('labelInfo/sampleStructure.json', 'r') as structureFile:
            sampleStructure = json.load(structureFile)
        path_to_dataset = {}
        with h5py.File(file_path, 'r') as file:
            file.visititems(lambda name, obj: sample_file_traversal(name, obj, path_to_dataset, False))
        if (path_to_dataset != sampleStructure):
            return jsonify({'file does not match structure'}), 400
        print("finished structure verifications")
        with h5py.File(file_path, 'r') as file:
            file.visititems(lambda name, obj: hdf5_ver_parsing(name, obj, path_to_dataset))
        output_json_path = os.path.join('output', 'nestedDict.json')
        with open(output_json_path, 'w') as json_file:
            json.dump(path_to_dataset, json_file, indent=True)

def sample_file_traversal(name, obj, path_to_dataset, labelCond):
    if isinstance(obj, h5py.Group):
        currentDataset = ""
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
        print(folders)
        for folder in folders[:-1]:
            current_dict = current_dict.setdefault(folder, {})
            filePath = filePath + folder + "->"
        dataset_name = folders[-1]
        current_dict[dataset_name] = os.path.join('output', filePath + dataset_name + '(insert_type)')
        if (labelCond):
            labels[filePath + dataset_name] = '(insert-label-here)'

def hdf5_ver_parsing(name, obj, path_to_dataset):
    if isinstance(obj, h5py.Group):
        currentDataset = ""
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
            filePath = filePath + folder + "->"
        dataset_name = folders[-1]
        with open('labelInfo/fileLabels.json', 'r') as file:
            labelsFinished = json.load(file)
        type = str(labelsFinished[filePath + dataset_name]).lower()
        if (type == 'images'):
            image_folder = os.path.join('output', filePath + dataset_name + "Images")
            os.makedirs(image_folder, exist_ok=True)
            imageDatasetHandling(obj, image_folder)
            current_dict[dataset_name] = image_folder
        elif (type == 'data'):
            try:
                data_path = os.path.join('output', filePath + dataset_name + "Data.npy")
                np.save(data_path, np.array(obj))
                current_dict[dataset_name] = data_path
            except Exception as e:
                print(data_path + " cannot be handled as data")
        elif (type == 'labels'):
            labels_path = os.path.join('output', filePath + dataset_name + "Labels.json")
            save_labels(obj, labels_path)
            current_dict[dataset_name] = labels_path

def traverse_hdf5(name, obj, path_to_dataset):
    if isinstance(obj, h5py.Group):
        currentDataset = ""
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
    # try:
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
    # except Exception as e:
    #     print("cannot be handled as labels")

def imageDatasetHandling(dataset, folder_name):
    # try:
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
    # except Exception as e:
    #     shutil.rmtree(folder_name)
    #     print(folder_name + " cannot be handled as an images folder")

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'h5', 'hdf5', 'dcm', 'dicom', 'nii', 'zip'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(debug=True)
