"""S3 upload utility — file storage spine."""
def put_object(key: str, body: str) -> None:
    """Upload an object to S3."""
    print(f"upload {key} {len(body)}")
