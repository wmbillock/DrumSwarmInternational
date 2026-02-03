import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { CommandCenter } from "./pages/CommandCenter";
import { ShowLibrary } from "./pages/ShowLibrary";
import { CorpsDeepDive } from "./pages/CorpsDeepDive";
import { CorpsList } from "./pages/CorpsList";
import { CorpsDetailV2 } from "./pages/CorpsDetailV2";
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
import { CompetitionDetail } from "./pages/CompetitionDetail";
import { SeasonWorkshop } from "./pages/SeasonWorkshop";
import { Settings } from "./pages/Settings";
import { SystemHealth } from "./pages/SystemHealth";
import { SystemHealthDashboard } from "./pages/SystemHealthDashboard";
import { SystemHealthDashboard } from "./pages/SystemHealthDashboard";
import MessageInbox from "./pages/MessageInbox";
import MessageArchive from "./pages/MessageArchive";
import MessageAdmin from "./pages/MessageAdmin";
import { StaffMarketplace } from "./pages/StaffMarketplace";
import { ScoreboardsPage } from "./pages/ScoreboardsPage";
import PerformanceExplorer from "./pages/PerformanceExplorer";
import { TourDashboard } from "./pages/TourDashboard";
import { CompetitionLive } from "./pages/CompetitionLive";
import { Finals } from "./pages/Finals";
import { CritiquePage } from "./pages/CritiquePage";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      // Lifecycle stages
      { path: "/design", element: <DesignRoom /> },
      { path: "/design/:showSlug", element: <DesignRoom /> },
      { path: "/shows", element: <ShowLibrary /> },
      { path: "/seasons", element: <SeasonWorkshop /> },
      { path: "/seasons/:seasonId", element: <SeasonWorkshop /> },
      { path: "/tour", element: <TourDashboard /> },
      { path: "/tour/:competitionId", element: <CompetitionLive /> },
      { path: "/finals", element: <Finals /> },
      { path: "/finals/:seasonId", element: <Finals /> },

      // Utilities
      { path: "/corps", element: <CorpsList /> },
      { path: "/corps/:corpsId", element: <CorpsDetailV2 /> },
      { path: "/corps/:corpsId/:tab", element: <CorpsDetailV2 /> },
      { path: "/", element: <CommandCenter /> },
      { path: "/settings", element: <Settings /> },

      // System & Messages (top nav)
      { path: "/system", element: <SystemHealth /> },
      { path: "/system-health", element: <SystemHealthDashboard /> },
      { path: "/system-health", element: <SystemHealthDashboard /> },
      { path: "/messages/inbox", element: <MessageInbox /> },
      { path: "/messages/archive", element: <MessageArchive /> },
      { path: "/messages/admin", element: <MessageAdmin /> },
      { path: "/scoreboards", element: <ScoreboardsPage /> },
      { path: "/metrics", element: <PerformanceExplorer /> },

      // Legacy routes — still accessible via deep links
      { path: "/corps-legacy/:corpsId", element: <CorpsDeepDive /> },
      { path: "/corps-legacy/:corpsId/:tab", element: <CorpsDeepDive /> },
      { path: "/runs", element: <RunsList /> },
      { path: "/runs/:runId", element: <RunDetail /> },
      { path: "/admin", element: <AdminChat /> },
      { path: "/templates", element: <Templates /> },
      { path: "/performers", element: <Performers /> },
      { path: "/seance", element: <Seance /> },
      { path: "/judging", element: <JudgingCritique /> },
      { path: "/judging/:corpsId", element: <JudgingCritique /> },
      { path: "/critique/:competitionId/:corpsId", element: <CritiquePage /> },
      { path: "/evolution", element: <EvolutionTalentPool /> },
      { path: "/staff", element: <StaffMarketplace /> },
      { path: "/history", element: <CorpsHistory /> },
      { path: "/history/:corpsId", element: <CorpsHistory /> },
      { path: "/seance-session/:seanceId", element: <SeanceSession /> },

      // Redirects from old routes
      { path: "/competitions", element: <Navigate to="/tour" replace /> },
      { path: "/competitions/:competitionId", element: <Navigate to="/tour" replace /> },
    ],
  },
]);
