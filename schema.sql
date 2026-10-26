-- STEP 2: CREATE DATABASE TABLES

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    phone VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE,
    role VARCHAR NOT NULL DEFAULT 'USER' CHECK (role IN ('USER', 'ADMIN', 'STAFF')),
    status VARCHAR NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'BLOCKED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. SECTORS
CREATE TABLE IF NOT EXISTS sectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR UNIQUE NOT NULL,
    slug VARCHAR UNIQUE NOT NULL,
    description TEXT,
    status VARCHAR DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. ORGANIZATIONS
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sector_id UUID REFERENCES sectors(id) ON DELETE RESTRICT,
    name VARCHAR NOT NULL,
    description TEXT,
    phone VARCHAR,
    email VARCHAR,
    address TEXT,
    city VARCHAR,
    state VARCHAR,
    pincode VARCHAR,
    status VARCHAR DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. BRANCHES
CREATE TABLE IF NOT EXISTS branches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    city VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    pincode VARCHAR,
    phone VARCHAR,
    latitude NUMERIC,
    longitude NUMERIC,
    opening_time TIME,
    closing_time TIME,
    status VARCHAR DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. SERVICES
CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sector_id UUID REFERENCES sectors(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT,
    average_service_time INTEGER NOT NULL CHECK (average_service_time >= 0),
    buffer_time INTEGER DEFAULT 0 CHECK (buffer_time >= 0),
    status VARCHAR DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. STAFF
CREATE TABLE IF NOT EXISTS staff (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    role VARCHAR NOT NULL DEFAULT 'STAFF',
    status VARCHAR DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. COUNTERS
CREATE TABLE IF NOT EXISTS counters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    counter_number INTEGER NOT NULL,
    status VARCHAR DEFAULT 'CLOSED' CHECK (status IN ('AVAILABLE', 'BUSY', 'CLOSED')),
    current_token_id UUID, -- Will be foreign key later to avoid circular dependency
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_branch_counter UNIQUE (branch_id, counter_number)
);

-- 8. APPOINTMENTS
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    sector_id UUID REFERENCES sectors(id) ON DELETE RESTRICT,
    organization_id UUID REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id UUID REFERENCES branches(id) ON DELETE RESTRICT,
    service_id UUID REFERENCES services(id) ON DELETE RESTRICT,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('BOOKED', 'CHECKED_IN', 'WAITING', 'CALLED', 'SERVING', 'COMPLETED', 'CANCELLED', 'NO_SHOW', 'SKIPPED')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. QUEUE TOKENS
CREATE TABLE IF NOT EXISTS queue_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID UNIQUE REFERENCES appointments(id) ON DELETE RESTRICT,
    token_number VARCHAR NOT NULL,
    queue_position INTEGER CHECK (queue_position >= 0),
    estimated_waiting_time INTEGER CHECK (estimated_waiting_time >= 0),
    status VARCHAR NOT NULL CHECK (status IN ('WAITING', 'CALLED', 'SERVING', 'COMPLETED', 'SKIPPED', 'NO_SHOW', 'CANCELLED')),
    counter_id UUID REFERENCES counters(id) ON DELETE SET NULL,
    called_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ADD CIRCULAR FOREIGN KEY TO COUNTERS
ALTER TABLE counters 
    ADD CONSTRAINT fk_current_token 
    FOREIGN KEY (current_token_id) REFERENCES queue_tokens(id) ON DELETE SET NULL;

-- 10. QUEUE EVENTS
CREATE TABLE IF NOT EXISTS queue_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES queue_tokens(id) ON DELETE CASCADE,
    event_type VARCHAR NOT NULL,
    previous_status VARCHAR,
    new_status VARCHAR NOT NULL,
    counter_id UUID REFERENCES counters(id) ON DELETE SET NULL,
    performed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    event_time TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- 11. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
    type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. OTP VERIFICATIONS
CREATE TABLE IF NOT EXISTS otp_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR NOT NULL,
    otp_hash VARCHAR NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    attempt_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. QR TOKENS
CREATE TABLE IF NOT EXISTS qr_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID UNIQUE REFERENCES appointments(id) ON DELETE CASCADE,
    queue_token_id UUID UNIQUE REFERENCES queue_tokens(id) ON DELETE CASCADE,
    secure_token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. REVIEWS
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    appointment_id UUID UNIQUE REFERENCES appointments(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_organizations_sector_id ON organizations(sector_id);
CREATE INDEX IF NOT EXISTS idx_branches_organization_id ON branches(organization_id);
CREATE INDEX IF NOT EXISTS idx_services_sector_id ON services(sector_id);
CREATE INDEX IF NOT EXISTS idx_staff_organization_id ON staff(organization_id);
CREATE INDEX IF NOT EXISTS idx_staff_branch_id ON staff(branch_id);
CREATE INDEX IF NOT EXISTS idx_counters_branch_id ON counters(branch_id);
CREATE INDEX IF NOT EXISTS idx_appointments_user_id ON appointments(user_id);
CREATE INDEX IF NOT EXISTS idx_appointments_sector_id ON appointments(sector_id);
CREATE INDEX IF NOT EXISTS idx_appointments_organization_id ON appointments(organization_id);
CREATE INDEX IF NOT EXISTS idx_appointments_branch_id ON appointments(branch_id);
CREATE INDEX IF NOT EXISTS idx_appointments_service_id ON appointments(service_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_queue_tokens_appointment_id ON queue_tokens(appointment_id);
CREATE INDEX IF NOT EXISTS idx_queue_tokens_status ON queue_tokens(status);
CREATE INDEX IF NOT EXISTS idx_queue_tokens_counter_id ON queue_tokens(counter_id);
CREATE INDEX IF NOT EXISTS idx_queue_tokens_created_at ON queue_tokens(created_at);
CREATE INDEX IF NOT EXISTS idx_queue_events_token_id ON queue_events(token_id);
CREATE INDEX IF NOT EXISTS idx_queue_events_time ON queue_events(event_time);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_qr_tokens_secure_token ON qr_tokens(secure_token);

-- SEED SECTORS (IF NOT EXISTS)
INSERT INTO sectors (id, name, slug, description)
VALUES 
    (uuid_generate_v4(), 'Hospital', 'hospital', 'Healthcare and Hospital sectors'),
    (uuid_generate_v4(), 'Bank', 'bank', 'Banking and Financial institutions'),
    (uuid_generate_v4(), 'Restaurant', 'restaurant', 'Food and Dining services'),
    (uuid_generate_v4(), 'Government Office', 'government-office', 'Public and Government services'),
    (uuid_generate_v4(), 'Retail', 'retail', 'Retail stores and outlets'),
    (uuid_generate_v4(), 'Supermarket', 'supermarket', 'Grocery and Supermarkets')
ON CONFLICT (slug) DO NOTHING;

-- SEED SERVICES (Linked to sectors dynamically)
DO $$
DECLARE
    h_id UUID;
    b_id UUID;
    r_id UUID;
    g_id UUID;
    re_id UUID;
    s_id UUID;
BEGIN
    SELECT id INTO h_id FROM sectors WHERE slug = 'hospital';
    SELECT id INTO b_id FROM sectors WHERE slug = 'bank';
    SELECT id INTO r_id FROM sectors WHERE slug = 'restaurant';
    SELECT id INTO g_id FROM sectors WHERE slug = 'government-office';
    SELECT id INTO re_id FROM sectors WHERE slug = 'retail';
    SELECT id INTO s_id FROM sectors WHERE slug = 'supermarket';

    -- Hospital Services
    INSERT INTO services (sector_id, name, average_service_time) VALUES
    (h_id, 'Doctor Consultation', 15), (h_id, 'Specialist Consultation', 20), (h_id, 'Laboratory', 10), (h_id, 'Pharmacy', 5), (h_id, 'Health Checkup', 30) ON CONFLICT DO NOTHING;

    -- Bank Services
    INSERT INTO services (sector_id, name, average_service_time) VALUES
    (b_id, 'Cash Counter', 5), (b_id, 'Account Opening', 25), (b_id, 'KYC', 10), (b_id, 'Loan Enquiry', 30), (b_id, 'Card Service', 15), (b_id, 'Money Transfer', 5) ON CONFLICT DO NOTHING;

    -- Restaurant Services
    INSERT INTO services (sector_id, name, average_service_time) VALUES
    (r_id, 'Table Booking', 0), (r_id, 'Dine-in', 45), (r_id, 'Takeaway', 10), (r_id, 'Billing', 5), (r_id, 'Customer Service', 10) ON CONFLICT DO NOTHING;

    -- Government Office Services
    INSERT INTO services (sector_id, name, average_service_time) VALUES
    (g_id, 'Certificate Service', 20), (g_id, 'Document Verification', 15), (g_id, 'Application Submission', 15), (g_id, 'Revenue Service', 30), (g_id, 'Grievance', 20), (g_id, 'Document Collection', 5) ON CONFLICT DO NOTHING;

    -- Retail Services
    INSERT INTO services (sector_id, name, average_service_time) VALUES
    (re_id, 'Customer Service', 15), (re_id, 'Product Assistance', 10), (re_id, 'Billing Assistance', 5), (re_id, 'Return / Exchange', 10), (re_id, 'Complaint', 20) ON CONFLICT DO NOTHING;

    -- Supermarket Services
    INSERT INTO services (sector_id, name, average_service_time) VALUES
    (s_id, 'Billing Counter', 5), (s_id, 'Customer Service', 10), (s_id, 'Product Return', 10), (s_id, 'Customer Help', 5), (s_id, 'Membership Service', 10) ON CONFLICT DO NOTHING;
END $$;
