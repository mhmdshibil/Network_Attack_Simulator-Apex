/**
 * Country flag + name utilities — Phase 5A.
 * getFlag: converts ISO 3166-1 alpha-2 code to an emoji flag via Unicode
 *          Regional Indicator Symbols (U+1F1E6–U+1F1FF).
 */

export function getFlag(code) {
  if (!code || code.length !== 2) return ''
  const upper = code.toUpperCase()
  return String.fromCodePoint(
    0x1F1E6 + upper.charCodeAt(0) - 65,
    0x1F1E6 + upper.charCodeAt(1) - 65,
  )
}

const NAMES = {
  AF: 'Afghanistan',  AL: 'Albania',      DZ: 'Algeria',
  AR: 'Argentina',    AU: 'Australia',    AT: 'Austria',
  AZ: 'Azerbaijan',   BD: 'Bangladesh',   BY: 'Belarus',
  BE: 'Belgium',      BR: 'Brazil',       BG: 'Bulgaria',
  CA: 'Canada',       CL: 'Chile',        CN: 'China',
  CO: 'Colombia',     HR: 'Croatia',      CZ: 'Czech Republic',
  DK: 'Denmark',      EG: 'Egypt',        ET: 'Ethiopia',
  FI: 'Finland',      FR: 'France',       DE: 'Germany',
  GH: 'Ghana',        GR: 'Greece',       HK: 'Hong Kong',
  HU: 'Hungary',      IN: 'India',        ID: 'Indonesia',
  IR: 'Iran',         IQ: 'Iraq',         IE: 'Ireland',
  IL: 'Israel',       IT: 'Italy',        JP: 'Japan',
  JO: 'Jordan',       KZ: 'Kazakhstan',   KE: 'Kenya',
  KR: 'South Korea',  KW: 'Kuwait',       LB: 'Lebanon',
  LY: 'Libya',        MY: 'Malaysia',     MX: 'Mexico',
  MA: 'Morocco',      NL: 'Netherlands',  NZ: 'New Zealand',
  NG: 'Nigeria',      NO: 'Norway',       PK: 'Pakistan',
  PE: 'Peru',         PH: 'Philippines',  PL: 'Poland',
  PT: 'Portugal',     QA: 'Qatar',        RO: 'Romania',
  RU: 'Russia',       SA: 'Saudi Arabia', SG: 'Singapore',
  ZA: 'South Africa', ES: 'Spain',        SE: 'Sweden',
  CH: 'Switzerland',  TW: 'Taiwan',       TH: 'Thailand',
  TN: 'Tunisia',      TR: 'Turkey',       UA: 'Ukraine',
  AE: 'UAE',          GB: 'United Kingdom', US: 'United States',
  UZ: 'Uzbekistan',   VN: 'Vietnam',      YE: 'Yemen',
}

export function getCountryName(code) {
  if (!code) return ''
  return NAMES[code.toUpperCase()] || code
}
