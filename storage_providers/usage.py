from storage_providers import LocalFilesystemProvider, GoogleDriveProvider
from storage_providers.config import load_config

config = load_config("config.yaml")
local = LocalFilesystemProvider("/home/user/docs")
drive = GoogleDriveProvider(account="personal", folder_id="root", config=config)

for doc in local.list_documents():
    print(doc.name)