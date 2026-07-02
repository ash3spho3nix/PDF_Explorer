# Storage Provider Framework – Architecture Design

## 1. Overall Architecture

The goal is to decouple the PDF inventory engine from the local filesystem. The **Scanner** will no longer use `pathlib` directly; instead, it will consume a **Storage Provider** abstraction. Each configured **root** (e.g., a local folder, a Google Drive account, a NAS share) will be backed by a concrete provider. The engine iterates over roots, calls `list_documents()`, and for each document calls `get_metadata()` and `open_stream()` to feed the extraction pipeline. The rest of the system (extractor, classifier, cache, IAM) remains unchanged.

```
┌─────────────────────────────────────────────────────────────┐
│                      Multi‑Root Configuration               │
│  root1: LocalFilesystemProvider("/home/user/docs")         │
│  root2: GoogleDriveProvider(account="personal")            │
│  root3: GoogleDriveProvider(account="work")                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Scanner (updated)                      │
│  for each root:                                            │
│    for each doc in provider.list_documents():              │
│      metadata = provider.get_metadata(doc.id)              │
│      stream = provider.open_stream(doc.id)                 │
│      → extractor.process(stream, metadata)                │
│      → classifier.classify()                               │
│      → cache.save()                                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Storage Providers Framework                   │
│  ┌───────────────┐  ┌──────────────────┐                   │
│  │ LocalProvider │  │ GoogleDriveProvider│                   │
│  └───────────────┘  └──────────────────┘                   │
│  ┌───────────────┐  ┌──────────────────┐                   │
│  │ OneDrive      │  │ S3               │ (extension points) │
│  └───────────────┘  └──────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

**Key principles**:
- Providers are **interchangeable** – the engine only depends on the abstract interface.
- **Read‑only** – providers never modify remote content; they only retrieve.
- **Incremental** – each provider supports change detection (via modified time or sync tokens).
- **Lazy downloading** – PDFs are downloaded only when needed for extraction (and cached locally).

---

## 2. Provider Interface (Abstract Base Class)

---

## 3. Package Layout

```
pdf_inventory/
├── storage_providers/
│   ├── __init__.py
│   ├── base.py                    # Abstract base classes
│   ├── local.py                   # LocalFilesystemProvider
│   ├── google_drive.py            # GoogleDriveProvider
│   ├── oauth.py                   # OAuth2 helper (for Google, OneDrive, etc.)
│   ├── cache.py                   # Local download cache manager
│   ├── config.py                  # Provider configuration loading
│   └── extensions/                # Placeholder for future providers
│       ├── onedrive.py
│       ├── dropbox.py
│       ├── s3.py
│       └── ...
├── scanner/
│   └── scanner.py                 # Updated to use providers
└── models/
    └── root.py                    # Root configuration model
```

---

## 4. Authentication Flow (Google Drive)

We use **OAuth2** with the official Google API Client Library.

1. **Register** the application in Google Cloud Console to obtain a `client_id` and `client_secret`.
2. **Authorization**:
   - On first run, the user is prompted to open a URL and grant permissions.
   - The redirect URI is `http://localhost:8080/` (or a custom port).
   - The resulting `authorization_code` is exchanged for a `refresh_token` and `access_token`.
3. **Token Storage**:
   - Tokens are stored per account in an encrypted file (using `keyring` or `cryptography`).
   - The encryption key can be derived from a user‑supplied password (or stored in the system keychain).
4. **Token Refresh**:
   - The provider automatically refreshes the access token when it expires using the refresh token.
   - If refresh fails, the provider raises an `AuthenticationError`; the engine can prompt the user to re‑authorize.

**Multiple accounts**:
- Each account is identified by a `account_name` (e.g., "personal", "work").
- Separate token files are stored for each account.

**Scopes required**:
- `https://www.googleapis.com/auth/drive.readonly` (read‑only access to all files).
- We can restrict to specific folders if needed.

---

## 5. Google Drive Synchronization Strategy

- **Initial full scan**:  
  - Use `drive.files.list` with `q="mimeType='application/pdf' and trashed=false"`.  
  - Paginate using `pageToken`.  
  - For each file, fetch metadata (name, parents, modifiedTime, size, etc.) and store in the local cache.  
  - Download the file only when its metadata is extracted (i.e., on demand).  
  - Store the local cache mapping from Drive `fileId` to local path.

- **Incremental sync**:
  - Use `drive.files.list` with `q` including `modifiedTime > 'YYYY-MM-DDTHH:mm:ss'` (the timestamp of last sync).  
  - Alternatively, use the `changes` API with a `pageToken` to get only changes. We'll implement the `changes` API for efficiency.  
  - The provider stores the `startPageToken` after each sync.  
  - On each incremental scan, we call `changes.list(pageToken=stored_token)` and process each change (added, modified, removed).  
  - After processing, we update the stored token to the new `startPageToken`.

- **Folder filtering**:
  - If the root is a specific folder (not "My Drive"), we filter using `q="'folder_id' in parents"`.
  - For "Shared Drives", we use `driveId` parameter.
  - For "Shared with me", we use `q="sharedWithMe=true"`.

- **Caching**:
  - Downloaded PDFs are stored in a local cache directory (e.g., `~/.pdf_inventory/cache/`).  
  - Cache entries are keyed by `fileId` + `modified_time` to detect updates.  
  - Old cache files are purged automatically (LRU or time‑based).

- **Selective downloading**:
  - Only download the PDF when `open_stream()` is called (which happens during extraction).  
  - For metadata extraction, we only need the file metadata (not the content).  
  - For first‑page extraction, we may need to download the whole file, but we can use the API to export only the first page? Possibly not; we'll download the full PDF and extract the first page locally.

---

## 6. SQLite Schema Changes

We need to augment the `pdf_index` table to store provider‑specific information.


These changes are backward‑compatible: existing rows will have `provider_type='local'` and `remote_id` equal to the local path (or NULL). The engine can still operate without these columns if they are missing, but the provider framework will populate them.

---

## 7. API Changes (Scanner Interface)

The scanner constructor now accepts a list of `Root` objects instead of a single `path`.

The `extractor` and `classifier` remain unchanged; they receive the document content (via stream) and metadata.

---

## 8. Integration Points

- **Multi‑Root Configuration**: The CLI will load a configuration file (YAML/JSON) that defines roots. Each root has a `type`, `provider` specific parameters (e.g., `folder_id`, `account`), and optional `exclude_patterns`.
- **Watch Mode**: For local providers, we can use filesystem watchers. For Google Drive, we will periodically poll using the `changes` API (or use push notifications if we set up a webhook, but that's more complex). The watch service will call the provider's `incremental_sync()` method and update the cache accordingly.
- **HTML Explorer**: The backend APIs will expose `provider_type`, `root_id`, `account_id`, `remote_path`, `sync_status` so the frontend can display cloud status, last sync, etc.
- **IAM & analysis**: All analysis modules already operate on `PDFFile` objects; they will now also contain the additional fields but will work identically.

---

## 9. Performance Analysis

- **Local provider**: `list_documents()` uses `pathlib.rglob` which is O(n) in number of files. We can still cache results.
- **Google Drive provider**:
  - `list_documents()`: API calls are paginated; each call returns ~100 files. For 10,000 PDFs, we need ~100 API calls. This is acceptable (a few seconds).
  - Metadata retrieval: We can fetch metadata for all files in one `list` call (we can request specific fields). No additional round trips.
  - `open_stream()`: Downloads the entire PDF. This is the most expensive operation. We only do this when extracting (classification, page count, etc.). With caching, we download only changed files.
  - Incremental sync: The `changes` API is efficient; it returns only changes since last sync.
  - We implement parallel downloads using `ThreadPoolExecutor` to speed up extraction.
- **Caching**: Local cache reduces network traffic. We store downloaded files in a local directory and only re‑download if `modified_time` changed.
- **Memory**: We stream the PDF content to the extractor; we don't load the whole file into memory at once.

---

## 10. Future Providers (Extension Points)

- **OneDrive** – use Microsoft Graph API, OAuth2, similar to Google Drive.
- **Dropbox** – use Dropbox API v2, OAuth2.
- **SharePoint** – use Microsoft Graph API (sites/drives).
- **NAS** – could use SMB/CIFS (via `smbclient`) or WebDAV.
- **Nextcloud** – use WebDAV (already supports `list`, `download`, etc.).
- **Amazon S3** – use boto3, list objects, download streams.
- **Generic WebDAV** – provide a `WebDAVProvider` that works with any WebDAV server.

All these can implement the same `StorageProvider` interface, so the scanner will work seamlessly.

---
