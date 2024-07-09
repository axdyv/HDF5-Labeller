import React, { useState, useEffect } from 'react';
import axios from 'axios';
import CustomFileUpload from '../../components/CustomFIleUploadField';
import Button from '@mui/material/Button';
import { Paper, FormControl, InputLabel, Select, MenuItem, CircularProgress } from '@mui/material';
import { LazyLoadImage } from 'react-lazy-load-image-component';
import Modal from 'react-modal';
import './style.css'
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import VisibilityIcon from '@mui/icons-material/Visibility';
import FolderIcon from '@mui/icons-material/Folder';
import BorderColorIcon from '@mui/icons-material/BorderColor';
import Dialog from '@mui/material/Dialog';

function MainPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [outputHDF5Files, setOutputHDF5Files] = useState([]);
  const [outputDICOMFiles, setOutputDICOMFiles] = useState([]);
  const [currentHDF5Path, setCurrentHDF5Path] = useState('');
  const [currentDICOMPath, setCurrentDICOMPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fileType, setFileType] = useState('');
  const [uploadingFileLoading, setUploadingFileLoading] = useState(false)

  const [modalIsOpen, setModalIsOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  const [imageGalleryModalIsOpen, setImageGalleryModalIsOpen] = useState(false);
  const [imageGallery, setImageGallery] = useState([]);
  const [labelGalleryModalIsOpen, setLabelGalleryModalIsOpen] = useState(false);
  const [labelGallery, setLabelGallery] = useState([]);
  const [metadataTextFiles, setMetadataTextFiles] = useState({});
  const [currentFolder, setCurrentFolder] = useState('');
  const [metadataTextModalIsOpen, setMetadataTextModalIsOpen] = useState(false);
  

  const handleFileChange = (files) => {
    setSelectedFile(files);
  };

  const handleUpload = () => {
    if (selectedFile) {
      const formData = new FormData();
      formData.append('file', selectedFile[0]);

      setUploadingFileLoading(true);
      axios.post(`http://127.0.0.1:5000/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      })
      .then(response => {
        console.log(`${fileType} file upload successful:`, response.data);
        fileType === 'HDF5' ? fetchOutputHDF5Files() : fetchOutputDICOMFiles(); // Refresh the output files list after upload
      })
      .catch(error => {
        console.error(`Error uploading ${fileType} file:`, error);
        setError(`Error uploading ${fileType} file.`);
      })
      .finally(() => {
        setUploadingFileLoading(false);
      });
    } else {
      setError('No file selected');
    }
  };

  const fetchOutputHDF5Files = (path = '') => {
    setLoading(true);
    axios.get(`http://127.0.0.1:5000/output-files?path=${path}`)
      .then(response => {
        console.log('Fetched HDF5 output files:', response.data);
        setOutputHDF5Files(response.data);
        setCurrentHDF5Path(path);
        setError(null);
      })
      .catch(error => {
        console.error('Error fetching HDF5 output files:', error);
        setError('Error fetching HDF5 output files.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const fetchOutputDICOMFiles = (path = '') => {
    setLoading(true);
    axios.get(`http://127.0.0.1:5000/output-files?path=${path}`)
      .then(response => {
        console.log('Fetched DICOM output files:', response.data);
        setOutputDICOMFiles(response.data);
        setCurrentDICOMPath(path);
        setError(null);
      })
      .catch(error => {
        console.error('Error fetching DICOM output files:', error);
        setError('Error fetching DICOM output files.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const downloadFile = (filename) => {
    setLoading(true);
    axios.get(`http://127.0.0.1:5000/output-files/${filename}`, {
      responseType: 'blob',
    })
    .then(response => {
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    })
    .catch(error => {
      console.error('Error downloading file:', error);
      setError('Error downloading file.');
    })
    .finally(() => {
      setLoading(false);
    });
  };

  const downloadFolder = (foldername) => {
    setLoading(true);
    axios.get(`http://127.0.0.1:5000/output-files/download-folder?folder=${foldername}`, {
      responseType: 'blob',
    })
    .then(response => {
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${foldername}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    })
    .catch(error => {
      console.error('Error downloading folder:', error);
      setError('Error downloading folder.');
    })
    .finally(() => {
      setLoading(false);
    });
  };

  const openModal = (file) => {
    setPreviewFile(file);
    setModalIsOpen(true);
  };

  const closeModal = () => {
    setPreviewFile(null);
    setModalIsOpen(false);
  };

  const openImageGalleryModal = (folder) => {
    axios.get(`http://127.0.0.1:5000/output-files/folder-images?folder=${folder}`)
      .then(response => {
        setImageGallery(response.data);
        setImageGalleryModalIsOpen(true);
      })
      .catch(error => {
        console.error('Error fetching folder images:', error);
        setError('Error fetching folder images.');
      });
  };

  const openLabelGalleryModal = (file, folder) => {
    axios.get(`http://127.0.0.1:5000/output-files/folder-images?folder=${folder}`)
      .then(response => {
        setLabelGallery(response.data);
        setLabelGalleryModalIsOpen(true);
      })
      .catch(error => {
        console.error('Error fetching folder images:', error);
        setError('Error fetching folder images.');
      });
  };

  const closeImageGalleryModal = () => {
    setImageGallery([]);
    setImageGalleryModalIsOpen(false);
  };

  const fetchMetadataAndTextFiles = (folder) => {
    setLoading(true);
    axios.get(`http://127.0.0.1:5000/output-files/folder-metadata-text?folder=${folder}`)
      .then(response => {
        setMetadataTextFiles(response.data);
        setCurrentFolder(folder);
        setError(null);
        setMetadataTextModalIsOpen(true);
      })
      .catch(error => {
        console.error('Error fetching metadata and text files:', error);
        setError('Error fetching metadata and text files.');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleHDF5DirectoryClick = (folder) => {
    const newPath = `${currentHDF5Path}/${folder}`;
    fetchOutputHDF5Files(newPath);
  };

  const handleDICOMDirectoryClick = (folder) => {
    const newPath = `${currentDICOMPath}/${folder}`;
    fetchOutputDICOMFiles(newPath);
  };

  const handleHDF5BackClick = () => {
    const pathSegments = currentHDF5Path.split('/').filter(segment => segment);
    pathSegments.pop();
    const newPath = pathSegments.join('/');
    fetchOutputHDF5Files(newPath);
  };

  const handleDICOMBackClick = () => {
    const pathSegments = currentDICOMPath.split('/').filter(segment => segment);
    pathSegments.pop();
    const newPath = pathSegments.join('/');
    fetchOutputDICOMFiles(newPath);
  };

  const renderHDF5Breadcrumbs = () => {
    const paths = currentHDF5Path.split('/').filter(path => path);
    return (
      <div className="breadcrumbs">
        <span onClick={() => fetchOutputHDF5Files('')}>Home</span>
        {paths.map((path, index) => (
          <span key={index} onClick={() => fetchOutputHDF5Files(paths.slice(0, index + 1).join('/'))}>
            {path}
          </span>
        ))}
      </div>
    );
  };

  const renderDICOMBreadcrumbs = () => {
    const paths = currentDICOMPath.split('/').filter(path => path);
    return (
      <div className="breadcrumbs">
        <span onClick={() => fetchOutputDICOMFiles('')}>Home</span>
        {paths.map((path, index) => (
          <span key={index} onClick={() => fetchOutputDICOMFiles(paths.slice(0, index + 1).join('/'))}>
            {path}
          </span>
        ))}
      </div>
    );
  };
  
  console.log('preview file ===>', previewFile)

  const renderMetadataTextModalContent = () => {
    const { metadata = {}, text = {} } = metadataTextFiles;

    return (
      <div>
        <h3>Metadata Files</h3>
        {Object.entries(metadata).map(([filename, content], index) => (
          <div key={index} className="metadata-file">
            <h4>{filename}</h4>
            <pre>{JSON.stringify(content, null, 2)}</pre>
          </div>
        ))}
        <h3>Text Files</h3>
        {Object.entries(text).map(([filename, content], index) => (
          <div key={index} className="text-file">
            <h4>{filename}</h4>
            <pre>{content}</pre>
          </div>
        ))}
      </div>
    );
  };

  return (
    <React.Fragment>
      <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
        <Paper elevation={3} style={{ width: '100%', margin: '0px 12px', padding: '12px' }}>
          <div>
            <h2 style={{marginBottom: 12}}>Upload HDF5 File</h2>
            <FormControl fullWidth margin="normal">
              <InputLabel id="file-type-label">File Type</InputLabel>
              <Select
                labelId="file-type-label"
                value={fileType}
                onChange={(e) => setFileType(e.target.value)}
              >
                <MenuItem value="HDF5">HDF5</MenuItem>
              </Select>
            </FormControl>
            <CustomFileUpload files={selectedFile} setFiles={handleFileChange} accept={fileType === 'HDF5' ? '.h5,.hdf5' : '.zip'} disabled={uploadingFileLoading || !fileType} />
            <Button onClick={handleUpload} variant="contained" style={{ width: '100%' }} disabled={!fileType || loading}>
              {uploadingFileLoading && <CircularProgress size={25}  style={{marginRight: '16px'}}/>} {uploadingFileLoading ? 'Uploading File' : 'Upload File'}
            </Button>
          </div>
          <div className="output-section">
            <h2>Output Files</h2>
            {error && <p className="error">{error}</p>}
            {fileType === 'HDF5' ? renderHDF5Breadcrumbs() : renderDICOMBreadcrumbs()}
            {fileType === 'HDF5' && currentHDF5Path && <button onClick={handleHDF5BackClick}>Back</button>}
            {fileType === 'DICOM' && currentDICOMPath && <button onClick={handleDICOMBackClick}>Back</button>}
            {fileType === 'HDF5' && (
              outputHDF5Files.length === 0 ? (
                <p>No HDF5 files available.</p>
              ) : (
                 <table>
                    {outputHDF5Files.map((file, index) => {
                      const isDirectory = !file.includes('.');
                      return (
                        <tr key={index}>
                          
                          {isDirectory 
                            ? <>
                                <td>
                                  <span onClick={() => handleHDF5DirectoryClick(file)} style={{ cursor: 'pointer', color: 'blue' }}>{file}</span>  
                                </td>
                                <td style={{display: 'flex', alignItems: 'center'}}>
                                  {<Tooltip title="Download File">
                                      <IconButton>
                                        <CloudDownloadIcon onClick={() => downloadFolder(file)} />  
                                      </IconButton>
                                    </Tooltip>
                                  }
                                  {<Tooltip title="View File">
                                      <IconButton>
                                        <VisibilityIcon onClick={() => openImageGalleryModal(file)}/>  
                                      </IconButton>
                                    </Tooltip>
                                  }
                                  {<Tooltip title="Label File">
                                      <IconButton>
                                        <BorderColorIcon onClick={() => openLabelGalleryModal(file)}/>  
                                      </IconButton>
                                    </Tooltip>
                                  }
                                </td>
                              </>
                            : <>
                                <td>
                                  <span onClick={() => openModal(`http://127.0.0.1:5000/output-files/${file}`)} style={{ cursor: 'pointer', color: 'blue' }}>{file}</span>  
                                </td>
                                <td>
                                  <Tooltip title="Download File">
                                    <IconButton>
                                      <CloudDownloadIcon onClick={() => downloadFile(file)}/>
                                    </IconButton>
                                  </Tooltip>
                                  <Tooltip title="Label File">
                                      <IconButton>
                                        <BorderColorIcon onClick={() => openModal(`http://127.0.0.1:5000/output-files/${file}`)}/>  
                                      </IconButton>
                                    </Tooltip>
                                </td>
                              </>
                            }
                          
                        </tr>
                      )
                    })}
                 </table>
                )
            )} 
            {fileType === 'DICOM' && (
              outputDICOMFiles.length === 0 ? (
                <p>No DICOM files available.</p>
              ) : (
                <table>
                  {outputDICOMFiles.map((file, index) => {
                    console.log('file ==>', file)
                    const isDirectory = !file.includes('.');
                    console.log('is directory====>', isDirectory)
                    return (
                      <tr key={index}>
                        {isDirectory && (
                          <>
                            <td>
                            <span>{file}</span>  
                            </td>
                            <td>
                              {<Tooltip title="Download Folder">
                                  <IconButton>
                                    <CloudDownloadIcon onClick={() => downloadFolder(file)} />  
                                  </IconButton>
                                </Tooltip>
                              }
                              {<Tooltip title="View Files">
                                  <IconButton>
                                    <VisibilityIcon onClick={() => fetchMetadataAndTextFiles(file)}/>  
                                  </IconButton>
                                </Tooltip>
                              }
                              {<Tooltip title="View Folder">
                                  <IconButton>
                                    <FolderIcon onClick={() => openImageGalleryModal(file)}/>  
                                  </IconButton>
                                </Tooltip>
                              }
                            </td>
                          </> 
                        )}
                      </tr>
                    );
                  })}
                </table>
              )
            )}
          </div>
        </Paper>
      </div>

      <Dialog open={modalIsOpen} onClose={closeModal} maxWidth="lg" fullWidth={true}>
        <div style={{ textAlign: 'center' }}>
          {previewFile && (
            <div>
              {previewFile.match(/.(jpeg|jpg|png|gif)$/i) ? (
                <img src={previewFile} alt="Preview" style={{ maxWidth: '100%', maxHeight: '80vh' }} />
              ) : (
                <iframe src={previewFile} style={{ width: '100%', height: '80vh' }} title="File Preview"></iframe>
              )}
            </div>
          )}
          <Button variant='contained' onClick={closeModal} style={{ marginTop: '20px' }}>Close</Button>
        </div>
      </Dialog>

      <Dialog open={imageGalleryModalIsOpen} onClose={closeImageGalleryModal} fullWidth={true} maxWidth="lg">
        <div style={{ textAlign: 'center' }}>
          <h2>Image Gallery</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center' }}>
            {imageGallery.map((image, index) => (
              <LazyLoadImage key={index} src={image} alt={`Gallery ${index}`} style={{ width: '200px', margin: '10px' }} />
            ))}
          </div>
          <Button variant='contained' onClick={closeImageGalleryModal} style={{ marginTop: '20px' }}>Close</Button>
        </div>
      </Dialog>

      <Dialog open={metadataTextModalIsOpen} onClose={() => setMetadataTextModalIsOpen(false)} style={{padding: '20px'}} maxWidth="lg" fullWidth={true}>
        <div style={{ textAlign: 'center' }}>
          <h2>Metadata and Text Files</h2>
          {renderMetadataTextModalContent()}
          <Button variant='contained' onClick={() => setMetadataTextModalIsOpen(false)} style={{ marginTop: '20px' }}>Close</Button>
        </div>
      </Dialog>
    </React.Fragment>
  );
}

export default MainPage;
