import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from common.models import User
from administration.models import AdminRoleMaster, AdminDesignationMaster, AdminUserDetails
from constants import PASS_PRE_SALT, PASS_POST_SALT

class Command(BaseCommand):
    help = "Creates or updates an active user with properly salted password and admin details"

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help="Username or phone number")
        parser.add_argument('--password', type=str, required=True, help="Raw plain-text password")
        parser.add_argument('--phone', type=str, default=None, help="10-digit phone number")
        parser.add_argument('--email', type=str, default=None, help="Email address")
        parser.add_argument('--role', type=str, default="SURVEY_ADMIN", help="Role code")
        parser.add_argument('--designation', type=str, default="SURVEYOR", help="Designation code")

    def handle(self, *args, **options):
        username = options['username']
        raw_password = options['password']
        phone = options['phone'] or (username if username.isdigit() and len(username) == 10 else "9000000000")
        email = options['email'] or f"{username}@gis.com"

        role_code = options['role']
        desig_code = options['designation']

        role_obj, _ = AdminRoleMaster.objects.get_or_create(
            role_code=role_code,
            defaults={
                "role_name": "Survey Administrator",
                "description": "Administrator of GIS surveys",
                "level": 1,
                "is_active": True
            }
        )

        designation_obj, _ = AdminDesignationMaster.objects.get_or_create(
            designation_code=desig_code,
            defaults={
                "designation_name": "Field Surveyor",
                "role": role_obj,
                "description": "GIS Field Surveyor",
                "hierarchy": 1,
                "is_active": True
            }
        )

        salted_password = PASS_PRE_SALT + raw_password + PASS_POST_SALT
        hashed_password = make_password(salted_password)

        user_obj, created = User.objects.get_or_create(
            username=username,
            defaults={
                "password": hashed_password,
                "phone": phone,
                "email": email,
                "user_type": 1,
                "role_id": role_obj.id,
                "designation_id": designation_obj.id,
                "level": 1,
                "is_active": True
            }
        )

        if not created:
            user_obj.password = hashed_password
            user_obj.phone = phone
            user_obj.email = email
            user_obj.is_active = True
            user_obj.save()
            self.stdout.write(self.style.SUCCESS(f"Updated existing user: {user_obj.username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Created new user: {user_obj.username}"))

        admin_detail_obj, d_created = AdminUserDetails.objects.get_or_create(
            user=user_obj,
            defaults={
                "first_name": "Surveyor",
                "last_name": username[-4:] if len(username) >= 4 else username,
                "mob_no": phone,
                "email": email,
                "role": role_obj,
                "designation": designation_obj,
                "is_active": True,
            }
        )

        self.stdout.write(self.style.SUCCESS(f"User {user_obj.username} is ready to login!"))
