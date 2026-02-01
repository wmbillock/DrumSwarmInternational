import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { CorpsMode } from "../types";
import * as v1 from "../services/v1";

interface ModeAction {
  label: string;
  command: string;
  description: string;
  style?: string;
}

interface ModeConfig {
  label: string;
  description: string;
  suggestedPrompts: string[];
  quickActions: ModeAction[];
}

const MODE_CONFIGS: Record<CorpsMode, ModeConfig> = {
  design_room: {
    label: "Design Room",
    description: "Creative collaboration — shape the show concept before rehearsal.",
    suggestedPrompts: [
      "Design the show structure with 3 movements",
      "Propose visual and musical themes",
      "Create segment breakdown for Movement 1",
      "Review the current design notes",
    ],
    quickActions: [
      { label: "Start Design", command: "resume_hut", description: "Wake agents to begin design", style: "primary" },
      { label: "Move to Rehearsal", command: "mode:rehearsal_mode", description: "Transition to rehearsal mode" },
    ],
  },
  rehearsal_mode: {
    label: "Rehearsal",
    description: "Iterative practice — agents work through segments, receive feedback, improve.",
    suggestedPrompts: [
      "Run basics for all sections",
      "Start sectionals for brass",
      "Check rehearsal progression",
      "What needs work before the run-through?",
    ],
    quickActions: [
      { label: "Basics", command: "basics", description: "Switch to basics mode" },
      { label: "Sectionals", command: "sectionals", description: "Switch to sectionals" },
      { label: "Full Ensemble", command: "full_ensemble", description: "Full ensemble rehearsal" },
      { label: "Run Through", command: "run_through", description: "Complete run-through", style: "primary" },
    ],
  },
  show_mode: {
    label: "Show Mode",
    description: "Live performance — execute the show with precision. No redesign allowed.",
    suggestedPrompts: [
      "Execute the show from the top",
      "Status report on current performance",
      "Flag any issues for post-show review",
      "How is the timing looking?",
    ],
    quickActions: [
      { label: "Go On Tour", command: "go_on_tour", description: "Full autonomous execution", style: "primary" },
      { label: "Attention", command: "attention", description: "All agents report status" },
    ],
  },
  judging: {
    label: "Judging",
    description: "Post-performance evaluation — judges score captions, identify issues.",
    suggestedPrompts: [
      "Show me the scoresheet",
      "What were the biggest issues?",
      "Run critique on the last performance",
      "Compare scores across captions",
    ],
    quickActions: [
      { label: "Run Critique", command: "attention", description: "Request full critique" },
      { label: "To Offseason", command: "mode:offseason_review", description: "Move to offseason review" },
    ],
  },
  offseason_review: {
    label: "Offseason",
    description: "Reflection and planning — review performance, plan improvements for next season.",
    suggestedPrompts: [
      "Summarize the season performance",
      "What improvements should we make?",
      "Review agent performance and ageouts",
      "Plan the next season",
    ],
    quickActions: [
      { label: "Season Transition", command: "season_transition", description: "Run end-of-season lifecycle" },
      { label: "New Season", command: "mode:design_room", description: "Start fresh in design room" },
    ],
  },
};

interface ModeContextType {
  mode: CorpsMode | null;
  config: ModeConfig | null;
  setMode: (corpsId: string, mode: CorpsMode) => Promise<void>;
  refreshMode: (corpsId: string) => Promise<void>;
}

const ModeContext = createContext<ModeContextType>({
  mode: null,
  config: null,
  setMode: async () => {},
  refreshMode: async () => {},
});

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<CorpsMode | null>(null);

  const config = mode ? MODE_CONFIGS[mode] : null;

  const refreshMode = useCallback(async (corpsId: string) => {
    try {
      const corps = await v1.getCorps(corpsId);
      if (corps.mode) {
        setModeState(corps.mode as CorpsMode);
      }
    } catch {}
  }, []);

  const setMode = useCallback(async (corpsId: string, newMode: CorpsMode) => {
    try {
      await v1.switchCorpsMode(corpsId, newMode);
      setModeState(newMode);
    } catch (e) {
      throw e;
    }
  }, []);

  return (
    <ModeContext.Provider value={{ mode, config, setMode, refreshMode }}>
      {children}
    </ModeContext.Provider>
  );
}

export function useMode() {
  return useContext(ModeContext);
}

export { MODE_CONFIGS };
export type { ModeConfig, ModeAction };
