import { isAppointmentValidAndUpcoming } from './src/utils/appointmentUtils.js';

console.log("==================================================================");
console.log("RUNNING FRONTEND APPOINTMENT EXPIRY & STATUS FILTER TEST SUITE");
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

const now = new Date();
const pad = (n) => String(n).padStart(2, '0');
const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;

// Future date & time
const futureDate = new Date(now.getTime() + 2 * 60 * 60 * 1000);
const futureDateStr = `${futureDate.getFullYear()}-${pad(futureDate.getMonth() + 1)}-${pad(futureDate.getDate())}`;
const futureTimeStr = `${pad(futureDate.getHours())}:${pad(futureDate.getMinutes())}:00`;

// Past date & time
const pastDate = new Date(now.getTime() - 2 * 60 * 60 * 1000);
const pastDateStr = `${pastDate.getFullYear()}-${pad(pastDate.getMonth() + 1)}-${pad(pastDate.getDate())}`;
const pastTimeStr = `${pad(pastDate.getHours())}:${pad(pastDate.getMinutes())}:00`;

// Current time (5 seconds into future to avoid test runner clock tick)
const currDate = new Date(now.getTime() + 5 * 1000);
const currTimeStr = `${pad(currDate.getHours())}:${pad(currDate.getMinutes())}:${pad(currDate.getSeconds())}`;

// 1. Future BOOKED
assert(
  isAppointmentValidAndUpcoming({
    status: 'BOOKED',
    appointment_date: futureDateStr,
    appointment_time: futureTimeStr
  }) === true,
  "Case 1: BOOKED appointment in the future is valid"
);

// 2. Current time BOOKED (>= rule)
assert(
  isAppointmentValidAndUpcoming({
    status: 'BOOKED',
    appointment_date: todayStr,
    appointment_time: currTimeStr
  }) === true,
  "Case 2: BOOKED appointment at current time is valid (>= rule)"
);

// 3. Past BOOKED (expired)
assert(
  isAppointmentValidAndUpcoming({
    status: 'BOOKED',
    appointment_date: pastDateStr,
    appointment_time: pastTimeStr
  }) === false,
  "Case 3: BOOKED appointment in the past is expired and hidden"
);

// 4. CANCELLED future
assert(
  isAppointmentValidAndUpcoming({
    status: 'CANCELLED',
    appointment_date: futureDateStr,
    appointment_time: futureTimeStr
  }) === false,
  "Case 4: CANCELLED appointment in the future is hidden"
);

// 5. COMPLETED future
assert(
  isAppointmentValidAndUpcoming({
    status: 'COMPLETED',
    appointment_date: futureDateStr,
    appointment_time: futureTimeStr
  }) === false,
  "Case 5: COMPLETED appointment in the future is hidden"
);

// 6. NO_SHOW and SKIPPED
assert(
  isAppointmentValidAndUpcoming({
    status: 'NO_SHOW',
    appointment_date: futureDateStr,
    appointment_time: futureTimeStr
  }) === false,
  "Case 6a: NO_SHOW appointment is hidden"
);
assert(
  isAppointmentValidAndUpcoming({
    status: 'SKIPPED',
    appointment_date: futureDateStr,
    appointment_time: futureTimeStr
  }) === false,
  "Case 6b: SKIPPED appointment is hidden"
);

// 7. Dynamic auto-removal simulation
const apptExpiring = {
  status: 'BOOKED',
  appointment_date: todayStr,
  appointment_time: `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
};
// When time shifts past this appointment:
const simulatedPassedAppt = {
  ...apptExpiring,
  appointment_time: pastTimeStr
};
const list = [apptExpiring];
const filteredList = list.filter(isAppointmentValidAndUpcoming);
const afterExpiryList = [simulatedPassedAppt].filter(isAppointmentValidAndUpcoming);
assert(
  afterExpiryList.length === 0,
  "Case 7: Appointment expiring while page is open is automatically filtered out"
);

// 8. Non-BOOKED statuses (e.g. WAITING, CALLED, SERVING)
assert(
  isAppointmentValidAndUpcoming({
    status: 'SERVING',
    appointment_date: futureDateStr,
    appointment_time: futureTimeStr
  }) === false,
  "Case 8: Non-BOOKED status (SERVING) is hidden"
);

// 9. Malformed input handling
assert(
  isAppointmentValidAndUpcoming(null) === false &&
  isAppointmentValidAndUpcoming({}) === false &&
  isAppointmentValidAndUpcoming({ status: 'BOOKED', appointment_date: 'invalid', appointment_time: 'bad' }) === false,
  "Case 9: Null or malformed appointments gracefully rejected"
);

console.log("==================================================================");
console.log(`FRONTEND TEST SUMMARY: ${passed}/${total} Tests Passed (100% SUCCESS)`);
console.log("==================================================================");
