/**
 * QueueLess AI — Live Date and Time Formatting Utilities
 *
 * Requirements:
 * - Browser local time with Asia/Kolkata (IST) fallback/support.
 * - Formats: "Monday, 26 October 2026" and "02:05:10 PM IST".
 * - Distinct from database synchronization timestamps.
 */

export const DEFAULT_TIMEZONE = 'Asia/Kolkata';

export const getEffectiveTimezone = () => {
  try {
    const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return localTz || DEFAULT_TIMEZONE;
  } catch {
    return DEFAULT_TIMEZONE;
  }
};

/**
 * Formats a Date object into a readable date string: e.g. "Monday, 26 October 2026"
 */
export const formatLiveDate = (date, timeZone = DEFAULT_TIMEZONE) => {
  if (!date) return '';
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return '';

  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone,
  }).format(d);
};

/**
 * Formats a Date object into a readable 12-hour time string: e.g. "02:05:10 PM"
 */
export const formatLiveTime = (date, timeZone = DEFAULT_TIMEZONE, includeSeconds = true) => {
  if (!date) return '';
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return '';

  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: includeSeconds ? '2-digit' : undefined,
    hour12: true,
    timeZone,
  }).format(d);
};

/**
 * Returns the short timezone code, e.g. "IST"
 */
export const getTimezoneAbbr = (timeZone = DEFAULT_TIMEZONE) => {
  if (timeZone === 'Asia/Kolkata' || timeZone === 'Asia/Calcutta') {
    return 'IST';
  }
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZoneName: 'short',
      timeZone,
    }).formatToParts(new Date());
    const tzPart = parts.find((p) => p.type === 'timeZoneName');
    return tzPart ? tzPart.value : '';
  } catch {
    return 'IST';
  }
};
