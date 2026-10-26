import uuid
from sqlalchemy import Column, String, Integer, Text, Numeric, Time, Date, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.sql import func
from app.db.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    role = Column(String, nullable=False, default="USER")
    status = Column(String, nullable=False, default="ACTIVE")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def customer_profile_id(self):
        """
        Explicit linked customer profile capability.
        Links customer/citizen operations (bookings, appointments, queue tokens)
        directly to this verified user identity without creating duplicate accounts.
        """
        return self.id

    @property
    def can_access_user_portal(self) -> bool:
        """
        Documented authorization capability allowing citizen User Portal access.
        Both regular USER and administrative ADMIN accounts possess citizen booking capabilities.
        """
        return self.status == "ACTIVE"

class Sector(Base):
    __tablename__ = "sectors"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="ACTIVE")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    organizations = relationship("Organization", back_populates="sector")
    services = relationship("Service", back_populates="sector")

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sector_id = Column(UUID(as_uuid=True), ForeignKey("sectors.id", ondelete="RESTRICT"))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    status = Column(String, default="ACTIVE")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    sector = relationship("Sector", back_populates="organizations")
    branches = relationship("Branch", back_populates="organization")

class Branch(Base):
    __tablename__ = "branches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    address = Column(Text, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    latitude = Column(Numeric, nullable=True)
    longitude = Column(Numeric, nullable=True)
    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)
    status = Column(String, default="ACTIVE")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    organization = relationship("Organization", back_populates="branches")
    counters = relationship("Counter", back_populates="branch")

class Service(Base):
    __tablename__ = "services"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sector_id = Column(UUID(as_uuid=True), ForeignKey("sectors.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    average_service_time = Column(Integer, nullable=False)
    buffer_time = Column(Integer, default=0)
    status = Column(String, default="ACTIVE")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    sector = relationship("Sector", back_populates="services")

class Staff(Base):
    __tablename__ = "staff"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"))
    role = Column(String, nullable=False, default="STAFF")
    status = Column(String, default="ACTIVE")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    branch = relationship("Branch", foreign_keys=[branch_id])

class Counter(Base):
    __tablename__ = "counters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    counter_number = Column(Integer, nullable=False)
    status = Column(String, default="CLOSED")
    current_token_id = Column(UUID(as_uuid=True), ForeignKey("queue_tokens.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    branch = relationship("Branch", back_populates="counters")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    sector_id = Column(UUID(as_uuid=True), ForeignKey("sectors.id", ondelete="RESTRICT"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="RESTRICT"))
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"))
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    status = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    sector = relationship("Sector", foreign_keys=[sector_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    branch = relationship("Branch", foreign_keys=[branch_id])
    service = relationship("Service", foreign_keys=[service_id])

class QueueToken(Base):
    __tablename__ = "queue_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="RESTRICT"), unique=True)
    token_number = Column(String, nullable=False)
    queue_position = Column(Integer, nullable=True)
    estimated_waiting_time = Column(Integer, nullable=True)
    status = Column(String, nullable=False)
    counter_id = Column(UUID(as_uuid=True), ForeignKey("counters.id", ondelete="SET NULL"), nullable=True)
    called_at = Column(TIMESTAMP(timezone=True), nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    counter = relationship("Counter", foreign_keys=[counter_id])

class QueueEvent(Base):
    __tablename__ = "queue_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(UUID(as_uuid=True), ForeignKey("queue_tokens.id", ondelete="CASCADE"))
    event_type = Column(String, nullable=False)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    counter_id = Column(UUID(as_uuid=True), ForeignKey("counters.id", ondelete="SET NULL"), nullable=True)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_time = Column(TIMESTAMP(timezone=True), server_default=func.now())
    metadata_ = Column("metadata", JSON, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class OTPVerification(Base):
    __tablename__ = "otp_verifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String, nullable=False)
    otp_hash = Column(String, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    verified = Column(Boolean, default=False)
    attempt_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class QRToken(Base):
    __tablename__ = "qr_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), unique=True)
    queue_token_id = Column(UUID(as_uuid=True), ForeignKey("queue_tokens.id", ondelete="CASCADE"), unique=True)
    secure_token = Column(String, unique=True, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Review(Base):
    __tablename__ = "reviews"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), unique=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
