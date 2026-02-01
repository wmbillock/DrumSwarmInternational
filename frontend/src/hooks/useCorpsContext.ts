import { useEffect, useRef } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useCorpsTheme } from "../contexts/CorpsThemeContext";
import * as api from "../services/api";

/**
 * Automatically manages corps theme based on current route context.
 *
 * When navigating to a corps-specific page (/corps/:corpsId), this hook:
 * 1. Saves the current user theme preference
 * 2. Loads and applies the corps-specific theme
 *
 * When navigating away from corps context, it:
 * 1. Restores the user's original theme preference
 */
export function useCorpsContext() {
  const location = useLocation();
  const params = useParams<{ corpsId?: string }>();
  const { setCorpsTheme } = useCorpsTheme();
  const userThemeRef = useRef<string | null>(null);
  const lastCorpsIdRef = useRef<string | null>(null);

  useEffect(() => {
    const currentCorpsId = params.corpsId;
    const isCorpsRoute = location.pathname.startsWith("/corps/") && currentCorpsId;

    // Entering corps context
    if (isCorpsRoute && currentCorpsId !== lastCorpsIdRef.current) {
      // Save user's theme preference if we haven't already
      if (userThemeRef.current === null) {
        userThemeRef.current = localStorage.getItem("dci-corps-theme") || "default";
      }

      // Load corps info and apply its theme
      api.getCorps(currentCorpsId)
        .then((corps) => {
          if (corps.theme_id) {
            setCorpsTheme(corps.theme_id);
          } else {
            // Fallback: try to match corps_id to theme_id
            setCorpsTheme(currentCorpsId);
          }
        })
        .catch(() => {
          // If corps not found, try using corps ID as theme ID
          setCorpsTheme(currentCorpsId);
        });

      lastCorpsIdRef.current = currentCorpsId;
    }
    // Leaving corps context
    else if (!isCorpsRoute && lastCorpsIdRef.current !== null) {
      // Restore user's original theme
      if (userThemeRef.current !== null) {
        setCorpsTheme(userThemeRef.current);
        userThemeRef.current = null;
      }
      lastCorpsIdRef.current = null;
    }
  }, [location.pathname, params.corpsId, setCorpsTheme]);
}
