// TypeScript types derived from actual forecast.json schema

export interface TeamForecast {
  id: string;        // FIFA 3-letter code
  name: string;
  group: string;     // A–L
  elo: number;
  elo_seed: number;
  p_title: number;
  p_final: number;
  p_sf: number;
  p_qf: number;
  p_r16: number;
  p_r32: number;
  p_group_win: number;
  p_group_second: number;
  p_third_advance: number;
  p_advance: number;
}

export interface GroupRow {
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
}

export interface LeverageEntry {
  team: string;
  p_title_by_outcome: [number, number, number];    // [homeWin, draw, awayWin]
  p_advance_by_outcome: [number, number, number];
  title_swing: number;
  advance_swing: number;
}

export interface Match {
  id: string;
  group: string;
  home: string;
  away: string;
  date: string;
  venue: string;
  played: boolean;
  hg: number | null;
  ag: number | null;
  // Only on unplayed matches
  probs?: { home: number; draw: number; away: number };
  attribution?: {
    home: Record<string, string | number>;
    away: Record<string, string | number>;
  };
  leverage?: LeverageEntry[];
  leverage_index?: number;
}

export interface TeamDist {
  team: string;
  p: number;
}

export interface BracketSlot {
  type: string;  // "R" = runner-up slot, etc.
  group?: string;
}

export interface BracketR32Match {
  match: number;
  date: string;
  venue: string;
  home_slot: BracketSlot;
  away_slot: BracketSlot;
  home_dist: TeamDist[];
  away_dist: TeamDist[];
  winner_dist: TeamDist[];
}

export interface BracketLaterMatch {
  match: number;
  date: string;
  venue: string;
  feeders?: number[];
  winner_dist: TeamDist[];
}

export interface BracketFinal {
  match: number;
  date: string;
  venue: string;
  winner_dist: TeamDist[];
}

export interface Bracket {
  r32: BracketR32Match[];
  r16: BracketLaterMatch[];
  qf: BracketLaterMatch[];
  sf: BracketLaterMatch[];
  final: BracketFinal;
}

export interface MarketData {
  fetched_at: string;
  implied: Record<string, number>;
}

export interface Forecast {
  generated_at: string;
  nsims: number;
  results_source: string;
  teams: TeamForecast[];
  groups: Record<string, GroupRow[]>;
  matches: Match[];
  bracket: Bracket;
  market: MarketData | null;
}

export interface HistoryRow {
  ts: string;
  team: string;
  p_title: number;
  p_final: number;
  p_sf: number;
  p_qf: number;
  p_advance: number;
  elo: number;
}
