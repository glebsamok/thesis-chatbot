import uuid

def generate_uuid():
    """Generate a new UUID."""
    return str(uuid.uuid4())

print(generate_uuid())