// Team names + flag rendering for all 48 World Cup 2026 teams.
//
// Flags are served as SVG images from flagcdn.com rather than emoji, because
// Windows deliberately omits country-flag emoji from its system font (they
// fall back to two-letter codes like "ES"). Image flags render identically on
// Windows, macOS, Android, and iOS.

import React from "react";

export const TEAM_NAMES: Record<string, string> = {
  MEX: "Mexico", RSA: "South Africa", KOR: "South Korea", CZE: "Czechia",
  CAN: "Canada", BIH: "Bosnia & Herzegovina", QAT: "Qatar", SUI: "Switzerland",
  BRA: "Brazil", MAR: "Morocco", HAI: "Haiti", SCO: "Scotland",
  USA: "United States", PAR: "Paraguay", AUS: "Australia", TUR: "Turkey",
  GER: "Germany", CUW: "Curaçao", CIV: "Ivory Coast", ECU: "Ecuador",
  NED: "Netherlands", JPN: "Japan", SWE: "Sweden", TUN: "Tunisia",
  BEL: "Belgium", EGY: "Egypt", IRN: "Iran", NZL: "New Zealand",
  ESP: "Spain", CPV: "Cape Verde", KSA: "Saudi Arabia", URU: "Uruguay",
  FRA: "France", SEN: "Senegal", IRQ: "Iraq", NOR: "Norway",
  ARG: "Argentina", ALG: "Algeria", AUT: "Austria", JOR: "Jordan",
  POR: "Portugal", COD: "DR Congo", UZB: "Uzbekistan", COL: "Colombia",
  ENG: "England", CRO: "Croatia", GHA: "Ghana", PAN: "Panama",
};

// FIFA 3-letter code -> flagcdn ISO code (subdivision codes for home nations)
export const TEAM_ISO: Record<string, string> = {
  MEX: "mx", RSA: "za", KOR: "kr", CZE: "cz", CAN: "ca", BIH: "ba",
  QAT: "qa", SUI: "ch", BRA: "br", MAR: "ma", HAI: "ht", SCO: "gb-sct",
  USA: "us", PAR: "py", AUS: "au", TUR: "tr", GER: "de", CUW: "cw",
  CIV: "ci", ECU: "ec", NED: "nl", JPN: "jp", SWE: "se", TUN: "tn",
  BEL: "be", EGY: "eg", IRN: "ir", NZL: "nz", ESP: "es", CPV: "cv",
  KSA: "sa", URU: "uy", FRA: "fr", SEN: "sn", IRQ: "iq", NOR: "no",
  ARG: "ar", ALG: "dz", AUT: "at", JOR: "jo", POR: "pt", COD: "cd",
  UZB: "uz", COL: "co", ENG: "gb-eng", CRO: "hr", GHA: "gh", PAN: "pa",
};

export function getName(teamId: string): string {
  return TEAM_NAMES[teamId] ?? teamId;
}

export function getFlagCode(teamId: string): string | undefined {
  return TEAM_ISO[teamId];
}

export function flagUrl(teamId: string): string | undefined {
  const code = TEAM_ISO[teamId];
  return code ? `https://flagcdn.com/${code}.svg` : undefined;
}

/** Inline flag image sized to a target height (px). Renders a neutral
 * placeholder of the same footprint for unknown ids so layout never shifts. */
export function Flag({
  id,
  h = 14,
  style = {},
  className = "",
}: {
  id: string;
  h?: number;
  style?: React.CSSProperties;
  className?: string;
}) {
  const url = flagUrl(id);
  if (!url) {
    return (
      <span
        className={className}
        style={{ display: "inline-block", width: Math.round(h * 1.4), height: h, ...style }}
      />
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt=""
      style={{
        height: h,
        width: "auto",
        borderRadius: 2,
        display: "inline-block",
        verticalAlign: "middle",
        boxShadow: "0 0 0 1px rgba(255,255,255,0.10)",
        flexShrink: 0,
        ...style,
      }}
      className={className}
      loading="lazy"
    />
  );
}
