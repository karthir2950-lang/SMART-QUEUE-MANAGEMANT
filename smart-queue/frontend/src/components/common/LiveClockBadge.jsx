import React, { useState, useEffect } from 'react';
import { formatLiveDate, formatLiveTime, getTimezoneAbbr, DEFAULT_TIMEZONE } from '../../utils/dateTimeUtils';

/**
 * LiveClockBadge
 *
 * Displays live updating date and time in the specified timezone (Asia/Kolkata IST by default).
 * Updates every second without page reloads.
 * Automatically cleans up interval timer on unmount.
 */
export default function LiveClockBadge({
  timeZone = DEFAULT_TIMEZONE,
  className = '',
  compact = false,
  showDate = true,
  showSeconds = true,
}) {
  const [currentDate, setCurrentDate] = useState(() => new Date());

  useEffect(() => {
    const timerId = setInterval(() => {
      setCurrentDate(new Date());
    }, 1000);

    return () => clearInterval(timerId);
  }, []);

  const formattedDate = formatLiveDate(currentDate, timeZone);
  const formattedTime = formatLiveTime(currentDate, timeZone, showSeconds);
  const tzAbbr = getTimezoneAbbr(timeZone);

  if (compact) {
    return (
      <div
        className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-xs font-mono font-bold text-[var(--color-text-main)] ${className}`}
        title={`Current Time: ${formattedDate} ${formattedTime} (${tzAbbr})`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span>{formattedTime}</span>
        <span className="text-[10px] text-[var(--color-secondary)] font-sans">{tzAbbr}</span>
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-2.5 px-3.5 py-2 rounded-2xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] shadow-xs transition-colors ${className}`}
      title={`Live Timezone: ${timeZone}`}
    >
      <div className="w-8 h-8 rounded-xl bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-sm font-bold flex-shrink-0">
        🕒
      </div>
      <div className="flex flex-col text-left leading-tight">
        {showDate && (
          <span className="text-[11px] font-semibold text-[var(--color-secondary)]">
            {formattedDate}
          </span>
        )}
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="text-xs sm:text-sm font-black font-mono tracking-tight text-[var(--color-text-main)]">
            {formattedTime}
          </span>
          <span className="px-1.5 py-0.5 rounded-md text-[9px] font-extrabold uppercase bg-[var(--color-accent-subtle)] text-[var(--color-primary)] font-mono">
            {tzAbbr}
          </span>
        </div>
      </div>
    </div>
  );
}
