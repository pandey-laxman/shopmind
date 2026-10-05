import argparse
from getpass import getpass
import logging

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from shopmind_api.core.database import SessionLocal
from shopmind_api.core.logging import configure_logging
from shopmind_api.repositories.customer_repository import CustomerRepository
from shopmind_api.schemas.auth import RegisterRequest
from shopmind_api.services.auth_service import AuthService
from shopmind_api.services.customer_service import CustomerEmailConflictError


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new ShopMind admin account")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    configure_logging()
    password = getpass("Admin password (at least 8 characters): ")
    if password != getpass("Confirm password: "):
        parser.exit(1, "Passwords do not match.\n")
    try:
        payload = RegisterRequest(name=args.name, email=args.email, password=password)
    except ValidationError:
        parser.exit(
            1, "Invalid name, email or password (8-1024 characters required).\n"
        )
    try:
        with SessionLocal() as db:
            admin = AuthService(CustomerRepository(db)).bootstrap_admin(payload)
            print(f"Created admin account with ID {admin.id}.")
    except CustomerEmailConflictError:
        parser.exit(1, "Email already exists; existing accounts are never promoted.\n")
    except SQLAlchemyError:
        logging.getLogger(__name__).exception("admin_bootstrap_database_error")
        parser.exit(1, "Database operation failed; check the application log.\n")


if __name__ == "__main__":
    main()
