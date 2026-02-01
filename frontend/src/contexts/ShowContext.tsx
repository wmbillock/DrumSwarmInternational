import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import type { Show } from "../types";
import * as v1 from "../services/v1";

interface ShowContextType {
  activeShow: Show | null;
  setActiveShow: (show: Show | null) => void;
  corpsId: string | null;
  rootCoordId: string | null;
  shows: Show[];
  refreshShows: () => Promise<void>;
  loading: boolean;
}

const ShowContext = createContext<ShowContextType>({
  activeShow: null,
  setActiveShow: () => {},
  corpsId: null,
  rootCoordId: null,
  shows: [],
  refreshShows: async () => {},
  loading: false,
});

export function ShowProvider({ children }: { children: ReactNode }) {
  const [activeShow, setActiveShowState] = useState<Show | null>(null);
  const [shows, setShows] = useState<Show[]>([]);
  const [loading, setLoading] = useState(false);

  const refreshShows = useCallback(async () => {
    setLoading(true);
    try {
      const data = await v1.listDBShows();
      // Map v1 response to Show type
      const shows: Show[] = data.map((item) => ({
        id: item.id,
        title: item.title,
        status: item.status as "draft" | "active" | "completed" | "archived",
        corps_id: item.corps_id,
        description: item.description,
      }));
      setShows(shows);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  const setActiveShow = useCallback((show: Show | null) => {
    setActiveShowState(show);
    if (show) {
      localStorage.setItem("dci-active-show", show.id);
    } else {
      localStorage.removeItem("dci-active-show");
    }
  }, []);

  // Load persisted show on mount
  useEffect(() => {
    refreshShows().then(async () => {
      const savedId = localStorage.getItem("dci-active-show");
      if (savedId) {
        try {
          // Find show in the list by ID
          const allShows = await v1.listDBShows();
          const show = allShows.find((s) => s.id === savedId);
          if (show) {
            const mappedShow: Show = {
              id: show.id,
              title: show.title,
              status: show.status as "draft" | "active" | "completed" | "archived",
              corps_id: show.corps_id,
              description: show.description,
            };
            setActiveShowState(mappedShow);
          } else {
            localStorage.removeItem("dci-active-show");
          }
        } catch {
          localStorage.removeItem("dci-active-show");
        }
      }
    });
  }, [refreshShows]);

  return (
    <ShowContext.Provider
      value={{
        activeShow,
        setActiveShow,
        corpsId: activeShow?.corps_id ?? null,
        rootCoordId: activeShow?.segment_root_id ?? null,
        shows,
        refreshShows,
        loading,
      }}
    >
      {children}
    </ShowContext.Provider>
  );
}

export function useShow() {
  return useContext(ShowContext);
}
