import re

MAX_NAME_LENGTH = 200
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")


def normalize_name(value):
    return str(value or "").strip()


def normalize_email(value):
    return str(value or "").strip()


def normalize_course(value):
    text = str(value or "").strip()
    return text or None


def is_valid_email(value):
    email = normalize_email(value)
    return bool(email) and bool(EMAIL_PATTERN.match(email))


def validate_recipient(recipient, seen_emails):
    name = normalize_name(recipient.get("name"))
    email = normalize_email(recipient.get("email"))
    course = normalize_course(recipient.get("course_or_role"))

    if not name:
        return False, "Name is required", name, email, course
    if len(name) > MAX_NAME_LENGTH:
        return False, "Name is too long", name, email, course
    if not is_valid_email(email):
        return False, "Email is invalid", name, email, course
    if email.lower() in seen_emails:
        return False, "Duplicate email within the same job", name, email, course

    seen_emails.add(email.lower())
    return True, "", name, email, course
