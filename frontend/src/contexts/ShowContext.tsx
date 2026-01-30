import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import type { Show } from "../types";
import { listShows, getShow } from "../services/api";

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
      const data = (await listShows()) as Show[];
      setShows(data);
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
          const show = (await getShow(savedId)) as Show;
          setActiveShowState(show);
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
        rootCoordId: activeShow?.coordinate_root_id ?? null,
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
