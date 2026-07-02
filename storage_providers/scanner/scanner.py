@dataclass
class Root:
    root_id: str
    provider: StorageProvider
    config: Dict[str, Any]   # provider‑specific config (e.g., folder_id, account)

class Scanner:
    def __init__(self, roots: List[Root]):
        self.roots = roots

    def scan(self, context: ScanContext) -> List[DocumentInfo]:
        all_docs = []
        for root in self.roots:
            docs = root.provider.list_documents()
            # Add root info to each doc (for storage in cache)
            for doc in docs:
                doc.root_id = root.root_id
                doc.provider_type = root.provider.get_identifier()
            all_docs.extend(docs)
        return all_docs