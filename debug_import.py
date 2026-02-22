import sys

print(f"Path: {sys.path}")
try:
    import fhir

    print(f"fhir: {fhir}")
    print(f"fhir file: {fhir.__file__}")
except ImportError as e:
    print(f"ImportError: {e}")

try:
    import fhir.resources

    print(f"fhir.resources: {fhir.resources}")
except ImportError as e:
    print(f"ImportError resources: {e}")
