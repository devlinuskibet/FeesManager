"""
Tenant middleware.

Resolves the current school for each request and attaches it as
request.school. Resolution order:

1. X-School-ID request header (numeric school primary key) — used by the
   bursar frontend after the user picks a school context.
2. Fall back to None — views requiring a school will return 403.

The lookup is done inside __call__ (not at import time) to avoid
app-registry circular imports, and uses only("id") to keep it cheap.
"""


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.school = None
        school_id = request.headers.get("X-School-ID")
        if school_id:
            # Import inside the method so the middleware can be imported
            # before apps are fully ready.
            from apps.tenants.models import School

            try:
                request.school = School.objects.only("id").get(pk=school_id)
            except (School.DoesNotExist, ValueError):
                request.school = None
        response = self.get_response(request)
        return response
