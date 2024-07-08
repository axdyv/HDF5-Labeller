import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";

import MainLayout from "../components/MainLayout";
import NotFoundPage from "../pages/NotFoundPage";


import MainPage from "../pages/MainPage";


const router = createBrowserRouter(
  [
    {
      path: "/projects",
      element: <MainLayout />,
      children: [
        {
          path: "",
          element:  <MainPage/>,
        },
      ],
    },
    {
      path: "/",
      element: <Navigate to="/projects" />,
    },

    { path: "*", element: <NotFoundPage /> },
  ],
  { basename: "/" }
);

function AppRoutes() {
  return <RouterProvider router={router} />;
}

export default AppRoutes;
