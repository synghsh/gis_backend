import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from common.models import User
from administration.models import AdminRoleMaster, AdminDesignationMaster, AdminUserDetails
from constants import PASS_PRE_SALT, PASS_POST_SALT, SUPER_ADMIN

class Command(BaseCommand):
    help = "Creates or updates the default super admin user superadmin@gis.com for GIS Admin FE login"

    def handle(self, *args, **options):
        self.stdout.write("Initializing default super admin user creation...")

        # 1. Create or get SUPER_ADMIN role
        role_obj, created = AdminRoleMaster.objects.get_or_create(
            role_code="SUPER_ADMIN",
            defaults={
                "role_name": "Super Administrator",
                "description": "Super Administrator of GIS platform",
                "level": 1,
                "is_active": True
            }
        )
        if created:
            self.stdout.write(f"Created role: {role_obj.role_name}")

        # 2. Create or get SUPER_ADMIN designation
        designation_obj, created = AdminDesignationMaster.objects.get_or_create(
            designation_code="SUPER_ADMIN_DESG",
            defaults={
                "designation_name": "Super Admin Designation",
                "role": role_obj,
                "description": "GIS Super Admin Designation",
                "hierarchy": 1,
                "is_active": True
            }
        )
        if created:
            self.stdout.write(f"Created designation: {designation_obj.designation_name}")

        # 3. Create/update user superadmin@gis.com
        raw_password = "SuperAdmin@2026"
        base64_encoded_dummy = "U3VwZXJBZG1pbkAyMDI2"
        salted_password = PASS_PRE_SALT + raw_password + PASS_POST_SALT
        hashed_password = make_password(salted_password)

        user_obj, created = User.objects.get_or_create(
            username="superadmin@gis.com",
            defaults={
                "password": hashed_password,
                "phone": "8888888888",
                "email": "superadmin@gis.com",
                "user_type": SUPER_ADMIN,
                "role_id": role_obj.id,
                "designation_id": designation_obj.id,
                "level": 1,
                "is_active": True
            }
        )

        if created:
            self.stdout.write(f"Created user: {user_obj.username}")
        else:
            self.stdout.write(f"User {user_obj.username} already exists, updating credentials.")
            user_obj.password = hashed_password
            user_obj.phone = "8888888888"
            user_obj.email = "superadmin@gis.com"
            user_obj.user_type = SUPER_ADMIN
            user_obj.role_id = role_obj.id
            user_obj.designation_id = designation_obj.id
            user_obj.save()

        # 4. Create/update admin details
        admin_detail_obj, created = AdminUserDetails.objects.get_or_create(
            user=user_obj,
            defaults={
                "first_name": "Super",
                "middle_name": "",
                "last_name": "Admin",
                "mob_no": "8888888888",
                "email": "superadmin@gis.com",
                "address": "GIS HQ",
                "district": "Kolkata",
                "state": "West Bengal",
                "pin": "700001",
                "joining_date": datetime.date(2026, 8, 8),
                "role": role_obj,
                "designation": designation_obj,
                "is_active": True
            }
        )

        if created:
            self.stdout.write(f"Created admin details for: {admin_detail_obj.first_name} {admin_detail_obj.last_name}")
        else:
            self.stdout.write(f"Admin details for user {user_obj.username} already exists, updating fields.")
            admin_detail_obj.first_name = "Super"
            admin_detail_obj.last_name = "Admin"
            admin_detail_obj.mob_no = "8888888888"
            admin_detail_obj.email = "superadmin@gis.com"
            admin_detail_obj.joining_date = datetime.date(2026, 8, 8)
            admin_detail_obj.role = role_obj
            admin_detail_obj.designation = designation_obj
            admin_detail_obj.save()

        self.stdout.write(self.style.SUCCESS("Default super admin user creation process completed!"))
        self.stdout.write(f"Username: {user_obj.username}")
        self.stdout.write(f"Password (raw): {raw_password}")
        self.stdout.write(f"Password (base64 for login): {base64_encoded_dummy}")
