import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/attendance"  # Try matching the actual DB

from app.core.database import SessionLocal
from app.models import Member
from app.schemas.member import MemberUpdate
from app.routers.members import update_member

db = SessionLocal()
admin = db.query(Member).filter_by(email="administrator@thetechlads.info").first()
target = db.query(Member).filter_by(email="member_test@thetechlads.info").first()

print("Target:", target.email)
update_data = MemberUpdate(first_name=target.first_name + "_test")
try:
    res = update_member(target.id, update_data, db=db, current_member=admin)
    print("Success:", res.first_name)
except Exception as e:
    import traceback
    traceback.print_exc()
