from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, exc, text, cast, Date
from datetime import datetime, date, time, timedelta, timezone
import secrets
import string
import uuid
from uuid import UUID
import io

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.domain import User, Appointment, Branch, Service, Sector, Organization, QueueToken, QueueEvent, QRToken
from app.schemas.queue import QueueTokenResponse, QueueVerifyResponse
from app.schemas.notification import AIPredictionResponse

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    import qrcode
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


router = APIRouter()

from app.services.token_service import (
    get_token_prefix,
    generate_secure_token,
    calculate_precise_people_ahead,
    issue_queue_token,
    enrich_token_response
)

@router.post("/token/{appointment_id}", response_model=QueueTokenResponse)
def create_queue_token(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify Appointment
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if str(appt.user_id) != str(current_user.id) and current_user.role not in ['ADMIN', 'STAFF']:
        raise HTTPException(status_code=403, detail="Not authorized to access this appointment")
        
    if appt.status != 'BOOKED':
        raise HTTPException(status_code=400, detail=f"Cannot generate token for {appt.status} appointment")
        
    sector = db.query(Sector).filter(Sector.id == appt.sector_id).first()
    org = db.query(Organization).filter(Organization.id == appt.organization_id).first()
    branch = db.query(Branch).filter(Branch.id == appt.branch_id).first()
    service = db.query(Service).filter(Service.id == appt.service_id).first()
    
    if not (sector and org and branch and service):
        raise HTTPException(status_code=400, detail="Related sector/branch/service missing")

    token = issue_queue_token(db, appt, current_user.id)
    db.commit()
    db.refresh(token)

    return enrich_token_response(db, token, appt, service, sector, org, branch)

@router.get("/active", response_model=Optional[QueueTokenResponse])
def get_active_user_queue_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_ids = [current_user.id]
    customer_pid = getattr(current_user, 'customer_profile_id', None)
    if customer_pid and customer_pid not in user_ids:
        user_ids.append(customer_pid)

    now_dt = datetime.now()
    now_date = now_dt.date()
    now_time = now_dt.time().replace(microsecond=0)

    # Find the earliest active, non-expired appointment for this user
    # Exclude CANCELLED, COMPLETED, NO_SHOW, and SKIPPED
    appt = db.query(Appointment).filter(
        Appointment.user_id.in_(user_ids),
        Appointment.status.notin_(['CANCELLED', 'COMPLETED', 'NO_SHOW', 'SKIPPED']),
        or_(
            Appointment.status.in_(['CALLED', 'SERVING', 'CHECKED_IN', 'WAITING']),
            and_(
                Appointment.status == 'BOOKED',
                or_(
                    Appointment.appointment_date > now_date,
                    and_(
                        Appointment.appointment_date == now_date,
                        Appointment.appointment_time >= now_time
                    )
                )
            )
        )
    ).order_by(
        Appointment.appointment_date.asc(),
        Appointment.appointment_time.asc()
    ).first()

    if not appt:
        return None

    token = db.query(QueueToken).filter(QueueToken.appointment_id == appt.id).first()
    if token and token.status in ('COMPLETED', 'CANCELLED', 'NO_SHOW', 'SKIPPED'):
        return None

    if not token:
        if appt.status == 'BOOKED':
            token = issue_queue_token(db, appt, current_user.id)
            db.commit()
            db.refresh(token)
        else:
            return None

    sector = db.query(Sector).filter(Sector.id == appt.sector_id).first()
    org = db.query(Organization).filter(Organization.id == appt.organization_id).first()
    branch = db.query(Branch).filter(Branch.id == appt.branch_id).first()
    service = db.query(Service).filter(Service.id == appt.service_id).first()

    return enrich_token_response(db, token, appt, service, sector, org, branch)

@router.get("/token/{appointment_id}", response_model=QueueTokenResponse)
def get_queue_token(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if str(appt.user_id) != str(current_user.id) and current_user.role not in ['ADMIN', 'STAFF']:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    token = db.query(QueueToken).filter(QueueToken.appointment_id == appointment_id).first()
    if not token:
        if appt.status == 'BOOKED':
            token = issue_queue_token(db, appt, current_user.id)
            db.commit()
            db.refresh(token)
        else:
            raise HTTPException(status_code=404, detail="Queue token not generated yet")
        
    sector = db.query(Sector).filter(Sector.id == appt.sector_id).first()
    org = db.query(Organization).filter(Organization.id == appt.organization_id).first()
    branch = db.query(Branch).filter(Branch.id == appt.branch_id).first()
    service = db.query(Service).filter(Service.id == appt.service_id).first()
    
    return enrich_token_response(db, token, appt, service, sector, org, branch)


@router.get("/token/{appointment_id}/prediction", response_model=AIPredictionResponse)
def get_queue_token_prediction(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if str(appt.user_id) != str(current_user.id) and current_user.role not in ['ADMIN', 'STAFF']:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    token = db.query(QueueToken).filter(QueueToken.appointment_id == appointment_id).first()
    if not token:
        if appt.status == 'BOOKED':
            token = issue_queue_token(db, appt, current_user.id)
            db.commit()
            db.refresh(token)
        else:
            raise HTTPException(status_code=404, detail="Queue token not generated yet")

    branch = db.query(Branch).filter(Branch.id == appt.branch_id).first()
    service = db.query(Service).filter(Service.id == appt.service_id).first()
    if not (branch and service):
        raise HTTPException(status_code=400, detail="Related branch or service missing")

    from app.services.prediction_service import calculate_ai_prediction
    return calculate_ai_prediction(db, token, appt, service, branch)



@router.get("/verify/{secure_token}", response_model=QueueVerifyResponse)
def verify_qr_token(secure_token: str, db: Session = Depends(get_db)):
    qr = db.query(QRToken).filter(QRToken.secure_token == secure_token).first()
    
    if not qr:
        return QueueVerifyResponse(valid=False, message="Invalid QR token")
        
    if qr.expires_at.replace(tzinfo=None) < datetime.utcnow():
        return QueueVerifyResponse(valid=False, message="QR token has expired")
        
    token = db.query(QueueToken).filter(QueueToken.id == qr.queue_token_id).first()
    appt = db.query(Appointment).filter(Appointment.id == qr.appointment_id).first()
    
    if not token or not appt:
        return QueueVerifyResponse(valid=False, message="Associated token or appointment not found")
        
    sector = db.query(Sector).filter(Sector.id == appt.sector_id).first()
    org = db.query(Organization).filter(Organization.id == appt.organization_id).first()
    branch = db.query(Branch).filter(Branch.id == appt.branch_id).first()
    service = db.query(Service).filter(Service.id == appt.service_id).first()
    
    people_ahead = calculate_precise_people_ahead(db, token, appt)
    
    return QueueVerifyResponse(
        valid=True,
        message="Valid Queue Token",
        token_number=token.token_number,
        sector=sector.name if sector else None,
        organization=org.name if org else None,
        branch=f"{branch.address}, {branch.city}" if branch else None,
        service=service.name if service else None,
        appointment_date=appt.appointment_date,
        appointment_time=appt.appointment_time,
        queue_status=token.status,
        queue_position=people_ahead + 1,
        people_ahead=people_ahead,
        estimated_waiting_time=people_ahead * (service.average_service_time + (service.buffer_time or 0)) if service else None
    )


@router.get("/token/{appointment_id}/pdf")
def download_token_pdf(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=500, detail="PDF generation library is not installed")
        
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if appt.user_id != current_user.id and current_user.role not in ['ADMIN', 'STAFF']:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    token = db.query(QueueToken).filter(QueueToken.appointment_id == appointment_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not generated yet")
        
    qr = db.query(QRToken).filter(QRToken.queue_token_id == token.id).first()
    
    sector = db.query(Sector).filter(Sector.id == appt.sector_id).first()
    org = db.query(Organization).filter(Organization.id == appt.organization_id).first()
    branch = db.query(Branch).filter(Branch.id == appt.branch_id).first()
    service = db.query(Service).filter(Service.id == appt.service_id).first()
    
    people_ahead = calculate_precise_people_ahead(db, token, appt)
    est_wait = people_ahead * (service.average_service_time + (service.buffer_time or 0)) if service else 0
    
    # Generate PDF in memory
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Draw Title
    p.setFont("Helvetica-Bold", 24)
    p.drawString(1 * inch, 10 * inch, "AI-Powered Universal Smart Queue")
    
    p.setFont("Helvetica-Bold", 18)
    p.drawString(1 * inch, 9.3 * inch, f"Queue Token: {token.token_number}")
    
    p.setFont("Helvetica", 12)
    y = 8.8 * inch
    line_height = 0.3 * inch
    
    p.drawString(1 * inch, y, f"Sector: {sector.name if sector else 'N/A'}")
    y -= line_height
    p.drawString(1 * inch, y, f"Organization: {org.name if org else 'N/A'}")
    y -= line_height
    p.drawString(1 * inch, y, f"Branch: {branch.city if branch else 'N/A'}")
    y -= line_height
    p.drawString(1 * inch, y, f"Service: {service.name if service else 'N/A'}")
    y -= line_height
    p.drawString(1 * inch, y, f"Appointment Date: {appt.appointment_date}")
    y -= line_height
    p.drawString(1 * inch, y, f"Appointment Time: {appt.appointment_time}")
    y -= line_height
    p.drawString(1 * inch, y, f"Status: {token.status}")
    y -= line_height
    p.drawString(1 * inch, y, f"Queue Position: {people_ahead + 1}")
    y -= line_height
    p.drawString(1 * inch, y, f"Initial Estimated Waiting Time: {est_wait} mins")
    
    # Generate QR Code image
    if qr:
        # Construct verification URL
        # For production, this should come from env. VITE_FRONTEND_URL or similar.
        # Fallback to a relative path that we assume frontend uses.
        import os
        base_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
        verify_url = f"{base_url}/verify/token/{qr.secure_token}"
        
        qr_img = qrcode.make(verify_url)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        # Draw QR on PDF
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(qr_buffer)
        p.drawImage(img_reader, 5 * inch, 7 * inch, width=2.5*inch, height=2.5*inch)
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=queue_token_{token.token_number}.pdf"})
