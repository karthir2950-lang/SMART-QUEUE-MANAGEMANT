import sys
import os
sys.path.insert(0, os.path.abspath("smart-queue/backend"))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    # search auth tables for 5173
    tables = ['flow_state', 'saml_relay_states', 'sso_providers', 'oauth_clients']
    for t in tables:
        try:
            res = conn.execute(text(f"SELECT * FROM auth.{t} WHERE CAST(row_to_json(auth.{t}) as text) LIKE '%5173%' LIMIT 5")).fetchall()
            print(f"Table auth.{t} has matches:", len(res))
            for r in res:
                print(r)
        except Exception as e:
            print(f"Table auth.{t} error:", e)
