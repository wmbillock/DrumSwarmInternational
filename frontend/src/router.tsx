import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { CommandCenter } from "./pages/CommandCenter";
import { SwarmOverview } from "./pages/SwarmOverview";
import { CorpsDeepDive } from "./pages/CorpsDeepDive";
import { CorpsList } from "./pages/CorpsList";
import { RunsList } from "./pages/RunsList";
import { RunDetail } from "./pages/RunDetail";
import { AdminChat } from "./pages/AdminChat";
import { Templates } from "./pages/Templates";
import { Performers } from "./pages/Performers";
import { Seance } from "./pages/Seance";
import { DesignRoom } from "./pages/DesignRoom";
import { JudgingCritique } from "./pages/JudgingCritique";
import { EvolutionTalentPool } from "./pages/EvolutionTalentPool";
import { CorpsHistory } from "./pages/CorpsHistory";
import { SeanceSession } from "./pages/SeanceSession";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <CommandCenter /> },
      { path: "/shows", element: <SwarmOverview /> },
      { path: "/corps", element: <CorpsList /> },
      { path: "/corps/:corpsId", element: <CorpsDeepDive /> },
      { path: "/corps/:corpsId/:tab", element: <CorpsDeepDive /> },
      { path: "/runs", element: <RunsList /> },
      { path: "/runs/:runId", element: <RunDetail /> },
      { path: "/admin", element: <AdminChat /> },
      { path: "/templates", element: <Templates /> },
      { path: "/performers", element: <Performers /> },
      { path: "/seance", element: <Seance /> },
      { path: "/design", element: <DesignRoom /> },
      { path: "/design/:showSlug", element: <DesignRoom /> },
      { path: "/judging", element: <JudgingCritique /> },
      { path: "/judging/:corpsId", element: <JudgingCritique /> },
      { path: "/evolution", element: <EvolutionTalentPool /> },
      { path: "/history", element: <CorpsHistory /> },
      { path: "/history/:corpsId", element: <CorpsHistory /> },
      { path: "/seance-session/:seanceId", element: <SeanceSession /> },
    ],
  },
]);
