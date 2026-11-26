# PATTERN: MIDDLEWARE-DJANGO-01 — Django middleware class
class DjangoMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request): return self.get_response(request)
    def process_request(self, request): pass
