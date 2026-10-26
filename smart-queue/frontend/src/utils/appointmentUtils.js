/**
 * QueueLess AI - Appointment Validation & Expiry Utilities
 *
 * Rules:
 * 1. Appointment status must be strictly 'BOOKED'.
 * 2. Scheduled appointment date and time must be >= current time in local timezone.
 * 3. Hides NO_SHOW, SKIPPED, CANCELLED, COMPLETED, or any other status besides BOOKED.
 * 4. Hides expired date/time values automatically.
 */

export const isAppointmentValidAndUpcoming = (app) => {
  if (!app || typeof app !== 'object') return false;
  if (app.status !== 'BOOKED') return false;
  if (!app.appointment_date || !app.appointment_time) return false;

  const dateStr = typeof app.appointment_date === 'string'
    ? app.appointment_date.split('T')[0]
    : '';

  let timeStr = typeof app.appointment_time === 'string' ? app.appointment_time : '';
  if (timeStr.includes('T')) {
    const parsedTime = new Date(timeStr);
    if (!isNaN(parsedTime.getTime())) {
      return parsedTime.getTime() >= Date.now();
    }
  }

  const timeParts = timeStr.split(':');
  if (timeParts.length < 2) return false;
  const hours = timeParts[0].padStart(2, '0');
  const minutes = timeParts[1].padStart(2, '0');
  const seconds = (timeParts[2] || '00').split('.')[0].padStart(2, '0');

  const dateParts = dateStr.split('-');
  if (dateParts.length !== 3) return false;
  const year = parseInt(dateParts[0], 10);
  const monthIndex = parseInt(dateParts[1], 10) - 1;
  const day = parseInt(dateParts[2], 10);

  const apptDate = new Date(
    year,
    monthIndex,
    day,
    parseInt(hours, 10),
    parseInt(minutes, 10),
    parseInt(seconds, 10)
  );

  if (isNaN(apptDate.getTime())) return false;

  return apptDate.getTime() >= Date.now();
};
