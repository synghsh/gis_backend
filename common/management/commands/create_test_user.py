import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from common.models import User
from administration.models import AdminRoleMaster, AdminDesignationMaster, AdminUserDetails
from constants import PASS_PRE_SALT, PASS_POST_SALT

class Command(BaseCommand):
    help = "Creates a test user and their admin user details for local verification"

    def handle(self, *args, **options):
        self.stdout.write("Initializing test user creation...")

        # 1. Create default role
        role_obj, created = AdminRoleMaster.objects.get_or_create(
            role_code="SURVEY_ADMIN",
            defaults={
                "role_name": "Survey Administrator",
                "description": "Administrator of GIS surveys",
                "level": 1,
                "is_active": True
            }
        )
        if created:
            self.stdout.write(f"Created role: {role_obj.role_name}")

        # 2. Create default designation
        designation_obj, created = AdminDesignationMaster.objects.get_or_create(
            designation_code="SURVEYOR",
            defaults={
                "designation_name": "Field Surveyor",
                "role": role_obj,
                "description": "GIS Field Surveyor",
                "hierarchy": 1,
                "is_active": True
            }
        )
        if created:
            self.stdout.write(f"Created designation: {designation_obj.designation_name}")

        # 3. Create user
        raw_password = "GisSurveyorPass@2026"
        base64_encoded_dummy = "R2lzU3VydmV5b3JQYXNzQDIwMjY="  # This is GisSurveyorPass@2026 base64 encoded
        salted_password = PASS_PRE_SALT + raw_password + PASS_POST_SALT
        hashed_password = make_password(salted_password)

        user_obj, created = User.objects.get_or_create(
            username="gis_surveyor",
            defaults={
                "password": hashed_password,
                "phone": "9876543210",
                "email": "surveyor@gis.com",
                "user_type": 1,
                "role_id": role_obj.id,
                "designation_id": designation_obj.id,
                "level": 1,
                "is_active": True
            }
        )

        if created:
            self.stdout.write(f"Created user: {user_obj.username}")
        else:
            self.stdout.write(f"User {user_obj.username} already exists, updating password.")
            user_obj.password = hashed_password
            user_obj.phone = "9876543210"
            user_obj.email = "surveyor@gis.com"
            user_obj.role_id = role_obj.id
            user_obj.designation_id = designation_obj.id
            user_obj.save()

        # 4. Create admin details
        admin_detail_obj, created = AdminUserDetails.objects.get_or_create(
            user=user_obj,
            defaults={
                "first_name": "Sayan",
                "middle_name": "",
                "last_name": "Ghosh",
                "mob_no": "9876543210",
                "email": "surveyor@gis.com",
                "address": "123 GIS Office Street",
                "district": "Kolkata",
                "state": "West Bengal",
                "pin": "700001",
                "joining_date": datetime.date(2026, 6, 14),
                "role": role_obj,
                "designation": designation_obj,
                "is_active": True
            }
        )

        if created:
            self.stdout.write(f"Created admin details for: {admin_detail_obj.first_name} {admin_detail_obj.last_name}")
        else:
            self.stdout.write(f"Admin details for user {user_obj.username} already exists, updating fields.")
            admin_detail_obj.first_name = "Sayan"
            admin_detail_obj.last_name = "Ghosh"
            admin_detail_obj.mob_no = "9876543210"
            admin_detail_obj.email = "surveyor@gis.com"
            admin_detail_obj.joining_date = datetime.date(2026, 6, 14)
            admin_detail_obj.role = role_obj
            admin_detail_obj.designation = designation_obj
            admin_detail_obj.save()

        self.stdout.write(self.style.SUCCESS("Test user creation process completed!"))
        self.stdout.write(f"Username: {user_obj.username}")
        self.stdout.write(f"Password (raw): {raw_password}")
        self.stdout.write(f"Password (base64 for login): {base64_encoded_dummy}")
