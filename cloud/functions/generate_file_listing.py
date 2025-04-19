def generate_file_listing():
    """
    Generates a static HTML listing of all files in the cloud bucket.
    """
    all_files = storage.Client().from_service_account_json().list_blobs("recordings")
