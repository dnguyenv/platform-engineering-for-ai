#!/usr/bin/env python
# Example CI script: check_schema_compatibility.py
import os
import sys
from confluent_kafka.schema_registry import SchemaRegistryClient, SchemaRegistryError
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry.avro import AvroSchema
# --- Configuration (Ideally passed via CI environment variables) ---
SCHEMA_REGISTRY_URL = os.environ.get("SCHEMA_REGISTRY_URL", "http://schema-registry.local:8081") # URL of the Schema Registry
SCHEMA_FILE_PATH = sys.argv[1] if len(sys.argv) > 1 else None # Path to the modified .avsc file in the PR
SCHEMA_SUBJECT = sys.argv[2] if len(sys.argv) > 2 else None   # Schema Registry subject name (e.g., "user-events-value")
def perform_compatibility_check():
    """Loads a schema, checks its compatibility via Schema Registry, and exits with appropriate status code."""
    if not SCHEMA_FILE_PATH or not SCHEMA_SUBJECT:
        print("Usage: python check_schema_compatibility.py <path_to_avsc_file> <schema_subject_name>", file=sys.stderr)
        sys.exit(2) # Indicate incorrect usage
    print(f"--- Schema Compatibility Check ---")
    print(f"Registry URL: {SCHEMA_REGISTRY_URL}")
    print(f"Schema File:  {SCHEMA_FILE_PATH}")
    print(f"Subject Name: {SCHEMA_SUBJECT}")
    print(f"---------------------------------")
    try:
        # 1. Load the proposed schema definition from the file
        with open(SCHEMA_FILE_PATH, 'r') as f:
            new_schema_string = f.read()
            proposed_schema = AvroSchema(new_schema_string)
        print("Proposed schema loaded successfully.")
        # 2. Initialize Schema Registry client
        schema_registry_conf = {'url': SCHEMA_REGISTRY_URL}
        schema_registry_client = SchemaRegistryClient(schema_registry_conf)
        print("Schema Registry client initialized.")
        # 3. Test compatibility against the subject's configured rule
        #    The registry compares the proposed schema against existing versions
        #    based on the compatibility level set for the subject (e.g., BACKWARD, FORWARD, FULL).
        print(f"Testing compatibility for subject '{SCHEMA_SUBJECT}'...")
        # Note: This checks against *all* registered versions by default per subject's config.
        # Use client.get_latest_version(SCHEMA_SUBJECT) and client.test_compatibility_against_version(...)
        # if specific version checks are needed.
        is_compatible = schema_registry_client.test_compatibility(subject=SCHEMA_SUBJECT, schema=proposed_schema)
        # 4. Handle the result
        if not is_compatible:
            # Compatibility check failed according to the registry's rules for this subject
            error_message = (
                f"FAIL: Proposed schema in '{SCHEMA_FILE_PATH}' is NOT compatible "
                f"with subject '{SCHEMA_SUBJECT}' based on its configured compatibility level.\n"
                f"Common breaking changes include removing/renaming fields or incompatible type changes.\n"
                f"Action Required: Revert incompatible changes or plan a MAJOR version bump with consumer coordination."
            )
            print(error_message, file=sys.stderr)
            sys.exit(1) # Exit with non-zero status code to fail the CI job
        else:
            # Compatibility check passed
            print(f"PASS: Proposed schema is compatible with subject '{SCHEMA_SUBJECT}'.")
            sys.exit(0) # Exit successfully

    except FileNotFoundError:
        print(f"Error: Schema file not found at '{SCHEMA_FILE_PATH}'", file=sys.stderr)
        sys.exit(1)
    except SchemaRegistryError as e:
        print(f"Error interacting with Schema Registry: {e}", file=sys.stderr)
        # Decide how to handle registry errors - fail safe?
        sys.exit(1)
    except Exception as e:
        # Catch other potential errors (e.g., invalid Avro schema format)
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
if __name__ == "__main__":
    perform_compatibility_check()
