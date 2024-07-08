import FileUpload from "react-material-file-upload"
import { useTheme } from '@mui/material/styles';

// interface IFileUpload {
//     files: File[],
//     setFiles: any,
//     buttonText?: string,
//     buttonStyle?: any,
//     label?: string,
//     name?: string,
//     disabled?: boolean
// }

const CustomFileUpload = (props) => {

    const theme = useTheme();
    const { files, setFiles, buttonStyle, label, disabled, accept } = props;
    return (
        <div style={{ marginBottom: '16px' }}>
            <FileUpload
                value={files}
                disabled={disabled}
                accept={accept}
                // This is the operator is so that we don't break other functionality
                onChange={(pickedFiles) => setFiles(pickedFiles)}
                buttonProps={{
                    variant: 'outlined',
                    size: 'small',
                    style: {
                        color: theme.palette.primary.main,
                        ...buttonStyle
                    },
                }}
                buttonText={label || "Select File"}
            />
        </div>

    )
}

CustomFileUpload.defaultProps = {
    buttonText: 'Select File',
    buttonStyle: {}
}
export default CustomFileUpload;