/**
 * QueueLess AI — Queue Token and Appointment Ordering Utilities
 *
 * Requirements:
 * - Natural/numeric token sorting: E.g. A-2 appears BEFORE A-10 (not alphabetical ASCII sort).
 * - Chronological appointment sorting: Earliest upcoming appointment date and time first.
 * - Active queue filtering: Excludes CANCELLED, COMPLETED, NO_SHOW, SKIPPED.
 * - Prevents mixing tokens across different branches, services, or queue dates.
 */

/**
 * Natural numeric comparison between two token identifiers or token objects.
 * Handles patterns such as "A-2" vs "A-10", "B-001" vs "B-002", etc.
 */
export const compareTokensNaturalOrder = (a, b) => {
  const tokenStrA = typeof a === 'string' ? a : (a?.token_number || '');
  const tokenStrB = typeof b === 'string' ? b : (b?.token_number || '');

  if (!tokenStrA && !tokenStrB) return 0;
  if (!tokenStrA) return 1;
  if (!tokenStrB) return -1;

  // Pattern: prefix (letters) followed by delimiter (- or _) and sequence number
  const regex = /^([A-Za-z]+)[-_]?(\d+)$/;
  const matchA = tokenStrA.match(regex);
  const matchB = tokenStrB.match(regex);

  if (matchA && matchB) {
    const prefixComp = matchA[1].toUpperCase().localeCompare(matchB[1].toUpperCase());
    if (prefixComp !== 0) return prefixComp;

    const numA = parseInt(matchA[2], 10);
    const numB = parseInt(matchB[2], 10);
    if (numA !== numB) return numA - numB;
  }

  // Fallback to standard Intl locale comparison with numeric collator
  return tokenStrA.localeCompare(tokenStrB, undefined, { numeric: true, sensitivity: 'base' });
};

/**
 * Sorts appointments in strict ascending chronological order:
 * Earliest upcoming scheduled date and time first.
 */
export const sortAppointmentsChronological = (appointments) => {
  if (!Array.isArray(appointments)) return [];

  return [...appointments].sort((a, b) => {
    const dateA = a.appointment_date ? String(a.appointment_date).split('T')[0] : '';
    const dateB = b.appointment_date ? String(b.appointment_date).split('T')[0] : '';
    if (dateA !== dateB) {
      return dateA.localeCompare(dateB);
    }

    const timeA = a.appointment_time ? String(a.appointment_time) : '';
    const timeB = b.appointment_time ? String(b.appointment_time) : '';
    return timeA.localeCompare(timeB);
  });
};

/**
 * Inactive terminal or non-waiting statuses that must be excluded from active queues.
 */
export const INACTIVE_TOKEN_STATUSES = new Set(['CANCELLED', 'COMPLETED', 'NO_SHOW', 'SKIPPED']);

/**
 * Filters and validates active queue tokens for a specific branch and service context.
 */
export const filterActiveQueueTokens = (tokens, options = {}) => {
  if (!Array.isArray(tokens)) return [];
  const { branchId, serviceId, queueDate } = options;

  return tokens.filter((t) => {
    if (!t) return false;

    // Exclude terminal non-active statuses
    const status = (t.status || '').toUpperCase();
    if (INACTIVE_TOKEN_STATUSES.has(status)) {
      return false;
    }

    // Isolate by branch if specified
    if (branchId && t.branch_id && String(t.branch_id) !== String(branchId)) {
      return false;
    }

    // Isolate by service if specified
    if (serviceId && t.service_id && String(t.service_id) !== String(serviceId)) {
      return false;
    }

    // Isolate by appointment/queue date if specified
    if (queueDate && t.appointment_date) {
      const tDate = String(t.appointment_date).split('T')[0];
      const qDate = String(queueDate).split('T')[0];
      if (tDate !== qDate) {
        return false;
      }
    }

    return true;
  });
};

/**
 * Sorts active queue tokens deterministically:
 * 1. Currently active/called tokens (SERVING, CALLED) first
 * 2. Scheduled appointment time ascending
 * 3. Token sequence order (natural numeric)
 * 4. Created timestamp ascending
 */
export const sortActiveQueueTokens = (tokens) => {
  if (!Array.isArray(tokens)) return [];

  return [...tokens].sort((a, b) => {
    const statusWeight = (s) => {
      if (s === 'SERVING') return 1;
      if (s === 'CALLED') return 2;
      if (s === 'WAITING') return 3;
      return 4;
    };

    const weightA = statusWeight(a.status);
    const weightB = statusWeight(b.status);
    if (weightA !== weightB) {
      return weightA - weightB;
    }

    // Next compare appointment date
    const dateA = a.appointment_date ? String(a.appointment_date).split('T')[0] : '';
    const dateB = b.appointment_date ? String(b.appointment_date).split('T')[0] : '';
    if (dateA !== dateB) {
      return dateA.localeCompare(dateB);
    }

    // Next compare appointment scheduled time
    const timeA = a.appointment_time ? String(a.appointment_time) : '';
    const timeB = b.appointment_time ? String(b.appointment_time) : '';
    if (timeA && timeB && timeA !== timeB) {
      return timeA.localeCompare(timeB);
    }

    // Next compare natural token sequence (e.g. A-2 before A-10)
    const tokenComp = compareTokensNaturalOrder(a.token_number, b.token_number);
    if (tokenComp !== 0) {
      return tokenComp;
    }

    // Finally created_at
    const createdA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const createdB = b.created_at ? new Date(b.created_at).getTime() : 0;
    return createdA - createdB;
  });
};
