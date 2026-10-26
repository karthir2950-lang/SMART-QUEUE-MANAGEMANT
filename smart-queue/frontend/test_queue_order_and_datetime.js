import { formatLiveDate, formatLiveTime, getTimezoneAbbr, DEFAULT_TIMEZONE } from './src/utils/dateTimeUtils.js';
import {
  compareTokensNaturalOrder,
  sortAppointmentsChronological,
  filterActiveQueueTokens,
  sortActiveQueueTokens,
  INACTIVE_TOKEN_STATUSES
} from './src/utils/queueOrderUtils.js';

console.log("==================================================================");
console.log("RUNNING LIVE DATE, TIME & CORRECT QUEUE ORDERING TEST SUITE");
console.log("==================================================================");

let passed = 0;
let total = 0;

function assert(condition, message) {
  total++;
  if (!condition) {
    console.error(`[FAIL] ${message}`);
    process.exit(1);
  } else {
    console.log(`[PASS] ${message}`);
    passed++;
  }
}

// -------------------------------------------------------------
// 1. Live Date & Time Formatting and Timezone Support
// -------------------------------------------------------------
const testDate = new Date('2026-10-26T14:30:00Z');
const istDateStr = formatLiveDate(testDate, 'Asia/Kolkata');
// 14:30 UTC is 20:00 IST on 26 October 2026
assert(
  istDateStr.includes('October') && istDateStr.includes('2026') && istDateStr.includes('26'),
  `Live date formatted correctly in readable format (${istDateStr})`
);

const istTimeStr = formatLiveTime(testDate, 'Asia/Kolkata');
assert(
  istTimeStr.includes('PM') || istTimeStr.includes('8:00'),
  `Live time formatted in readable 12-hour format with PM (${istTimeStr})`
);

const istAbbr = getTimezoneAbbr('Asia/Kolkata');
assert(
  istAbbr === 'IST',
  `Timezone abbreviation for Asia/Kolkata is IST (${istAbbr})`
);

// -------------------------------------------------------------
// 2. Correct Queue Token Ordering (Natural/Numeric, not ASCII)
// -------------------------------------------------------------
// Critical Requirement: "A-10 appearing before A-2 must be prevented"
const unorderedTokens = ['A-10', 'A-2', 'A-1', 'A-20', 'A-3', 'B-1', 'B-10', 'B-2'];
const sortedTokens = [...unorderedTokens].sort(compareTokensNaturalOrder);

assert(
  sortedTokens.indexOf('A-2') < sortedTokens.indexOf('A-10'),
  "Natural Token Ordering: 'A-2' correctly appears BEFORE 'A-10'"
);
assert(
  sortedTokens.indexOf('A-1') < sortedTokens.indexOf('A-2'),
  "Natural Token Ordering: 'A-1' correctly appears BEFORE 'A-2'"
);
assert(
  sortedTokens.indexOf('A-10') < sortedTokens.indexOf('A-20'),
  "Natural Token Ordering: 'A-10' correctly appears BEFORE 'A-20'"
);
assert(
  sortedTokens.indexOf('B-2') < sortedTokens.indexOf('B-10'),
  "Natural Token Ordering: 'B-2' correctly appears BEFORE 'B-10'"
);

// Standard zero-padded tokens (B-001, B-002, B-010)
const zeroPaddedTokens = ['B-010', 'B-002', 'B-001'];
const sortedZeroPadded = [...zeroPaddedTokens].sort(compareTokensNaturalOrder);
assert(
  sortedZeroPadded[0] === 'B-001' && sortedZeroPadded[1] === 'B-002' && sortedZeroPadded[2] === 'B-010',
  "Zero-padded token ordering: B-001, B-002, B-010"
);

// -------------------------------------------------------------
// 3. Chronological Appointment Ordering (Earliest upcoming first)
// -------------------------------------------------------------
const mixedAppointments = [
  { id: '3', appointment_date: '2026-10-27', appointment_time: '09:00:00' },
  { id: '1', appointment_date: '2026-10-26', appointment_time: '14:30:00' },
  { id: '2', appointment_date: '2026-10-26', appointment_time: '16:00:00' },
  { id: '4', appointment_date: '2026-10-27', appointment_time: '11:15:00' }
];

const sortedAppts = sortAppointmentsChronological(mixedAppointments);
assert(
  sortedAppts[0].id === '1' && sortedAppts[1].id === '2' && sortedAppts[2].id === '3' && sortedAppts[3].id === '4',
  "Appointments sorted in strict ascending chronological order: earliest upcoming first"
);

// -------------------------------------------------------------
// 4. Token Queue Exclusion & Distinction Rules
// -------------------------------------------------------------
const rawTokens = [
  { id: 't1', token_number: 'A-1', status: 'SERVING', branch_id: 'b1', service_id: 's1' },
  { id: 't2', token_number: 'A-2', status: 'WAITING', branch_id: 'b1', service_id: 's1' },
  { id: 't3', token_number: 'A-3', status: 'COMPLETED', branch_id: 'b1', service_id: 's1' },
  { id: 't4', token_number: 'A-4', status: 'CANCELLED', branch_id: 'b1', service_id: 's1' },
  { id: 't5', token_number: 'A-5', status: 'NO_SHOW', branch_id: 'b1', service_id: 's1' },
  { id: 't6', token_number: 'A-6', status: 'SKIPPED', branch_id: 'b1', service_id: 's1' },
  { id: 't7', token_number: 'A-10', status: 'WAITING', branch_id: 'b1', service_id: 's1' },
  { id: 't8', token_number: 'A-7', status: 'WAITING', branch_id: 'b2', service_id: 's1' }, // different branch
];

// Exclusion check
const activeTokensBranch1 = filterActiveQueueTokens(rawTokens, { branchId: 'b1', serviceId: 's1' });
const activeStatuses = activeTokensBranch1.map(t => t.status);
assert(
  !activeStatuses.includes('COMPLETED') &&
  !activeStatuses.includes('CANCELLED') &&
  !activeStatuses.includes('NO_SHOW') &&
  !activeStatuses.includes('SKIPPED'),
  "COMPLETED, CANCELLED, NO_SHOW, and SKIPPED tokens are strictly excluded from active queue"
);

// Cross-branch isolation check
assert(
  !activeTokensBranch1.some(t => t.branch_id === 'b2'),
  "Tokens from different branches are strictly NOT mixed"
);

// Serving vs Next Waiting distinction
const sortedActive = sortActiveQueueTokens(activeTokensBranch1);
assert(
  sortedActive[0].status === 'SERVING',
  "Currently SERVING token is distinct and prioritised before WAITING tokens"
);
assert(
  sortedActive[1].token_number === 'A-2' && sortedActive[2].token_number === 'A-10',
  "WAITING tokens are sorted in correct natural sequence: A-2 before A-10"
);

console.log("==================================================================");
console.log(`FRONTEND TEST SUMMARY: ${passed}/${total} Tests Passed (100% SUCCESS)`);
console.log("==================================================================");
