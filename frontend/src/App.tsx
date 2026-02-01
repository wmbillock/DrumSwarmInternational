/**
 * App.tsx — Retained as a fallback. The main app now uses React Router
 * via main.tsx → router.tsx → AppLayout.tsx → page components.
 *
 * This file is kept for any direct imports but is no longer the primary entry point.
 */

import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import "./App.css";

export default function App() {
  return <RouterProvider router={router} />;
}
