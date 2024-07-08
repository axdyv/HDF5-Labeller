import { Outlet } from "react-router-dom";
import Header from "../Header";
import { Box } from "@mui/material";

const MainLayout = () => {

    return (
        <>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <Header />
                <Box sx={{ display: 'flex', padding: { xs: '10px', sm: '14px 25px' }, width: 'auto' }}>
                    <Outlet />
                </Box>
            </div>
        </>
    )
}


export default MainLayout

