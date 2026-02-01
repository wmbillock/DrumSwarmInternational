import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { SwarmOverview } from "./pages/SwarmOverview";
import { CorpsDeepDive } from "./pages/CorpsDeepDive";
import { AdminChat } from "./pages/AdminChat";
import { Templates } from "./pages/Templates";
import { Performers } from "./pages/Performers";
import { Seance } from "./pages/Seance";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <SwarmOverview /> },
      { path: "/corps/:corpsId", element: <CorpsDeepDive /> },
      { path: "/corps/:corpsId/:tab", element: <CorpsDeepDive /> },
      { path: "/admin", element: <AdminChat /> },
      { path: "/templates", element: <Templates /> },
      { path: "/performers", element: <Performers /> },
      { path: "/seance", element: <Seance /> },
    ],
  },
]);
